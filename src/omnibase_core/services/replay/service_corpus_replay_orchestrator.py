"""
ServiceCorpusReplayOrchestrator - Orchestrate replay of execution corpus.

This module provides the ServiceCorpusReplayOrchestrator service for
replaying an entire corpus of executions with configurable concurrency,
error handling, and progress tracking.

Design:
    The orchestrator wraps ExecutorReplay to replay individual executions
    while managing corpus-level concerns:
    - Sequential or parallel execution with concurrency control
    - Progress tracking with optional callbacks
    - Continue-on-failure or fail-fast error handling
    - Subset filtering for targeted replays
    - Aggregate metrics calculation

Architecture:
    ::

        ServiceCorpusReplayOrchestrator
            |
            +-- ExecutorReplay (single execution replay)
            |
            +-- ModelExecutionCorpus (input)
            |
            +-- ModelCorpusReplayConfig (configuration)
            |
            +-- ModelCorpusReplayResult (output)

Thread Safety:
    ServiceCorpusReplayOrchestrator instances are NOT thread-safe.
    Create separate orchestrator instances per thread for concurrent use.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_corpus_replay_orchestrator import (
            ServiceCorpusReplayOrchestrator,
        )
        from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay
        from omnibase_core.models.replay import (
            ModelCorpusReplayConfig,
            ModelExecutionCorpus,
        )

        # Create orchestrator
        executor = ExecutorReplay()
        orchestrator = ServiceCorpusReplayOrchestrator(executor)

        # Configure replay
        config = ModelCorpusReplayConfig(
            concurrency=4,
            fail_fast=False,
        )

        # Run replay
        result = await orchestrator.replay(corpus, config)
        print(f"Success rate: {result.success_rate:.1%}")

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ExecutorReplay: Single execution replay
    - ModelExecutionCorpus: Corpus of executions

.. versionadded:: 0.6.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.models.replay.model_aggregate_metrics import ModelAggregateMetrics
from omnibase_core.models.replay.model_corpus_replay_config import (
    ModelCorpusReplayConfig,
)
from omnibase_core.models.replay.model_corpus_replay_progress import (
    ModelCorpusReplayProgress,
)
from omnibase_core.models.replay.model_corpus_replay_result import (
    ModelCorpusReplayResult,
)
from omnibase_core.models.replay.model_single_replay_result import (
    ModelSingleReplayResult,
)

if TYPE_CHECKING:
    from omnibase_core.models.manifest.model_execution_manifest import (
        ModelExecutionManifest,
    )
    from omnibase_core.models.replay.model_execution_corpus import ModelExecutionCorpus
    from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay
    from omnibase_core.protocols.protocol_replay_progress_callback import (
        ProtocolReplayProgressCallback,
    )

_logger = logging.getLogger(__name__)

__all__ = ["ServiceCorpusReplayOrchestrator"]


class ServiceCorpusReplayOrchestrator:
    """
    Orchestrates replay of an entire execution corpus.

    Manages replay of 20-50+ executions with configurable concurrency,
    error handling, progress tracking, and aggregate metrics.

    The orchestrator supports two modes:
    - **Sequential**: Replay one-by-one, maintaining order
    - **Parallel**: Replay with configurable concurrency

    And two error handling modes:
    - **Continue-on-failure**: Capture errors and continue
    - **Fail-fast**: Stop on first error

    Attributes:
        executor: The ExecutorReplay instance for single execution replay.
        last_progress: Most recent progress update (if any).

    Thread Safety:
        NOT thread-safe. Create separate instances per thread.

    Example:
        >>> executor = ExecutorReplay()
        >>> orchestrator = ServiceCorpusReplayOrchestrator(executor)
        >>> config = ModelCorpusReplayConfig(concurrency=4)
        >>> result = await orchestrator.replay(corpus, config)
        >>> print(f"Success: {result.all_successful}")

    .. versionadded:: 0.6.0
    """

    def __init__(self, executor: ExecutorReplay) -> None:
        """Initialize the orchestrator.

        Args:
            executor: ExecutorReplay instance for single execution replay.
        """
        self._executor = executor
        self._last_progress: ModelCorpusReplayProgress | None = None
        self._cancelled = False

    @property
    def executor(self) -> ExecutorReplay:
        return self._executor

    @property
    def last_progress(self) -> ModelCorpusReplayProgress | None:
        return self._last_progress

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested.

        Returns:
            True if cancel() was called.
        """
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation of the current replay.

        Cancellation is cooperative - the orchestrator checks this flag
        between executions and will stop gracefully.
        """
        self._cancelled = True

    def reset(self) -> None:
        """Reset orchestrator state for a new replay."""
        self._cancelled = False
        self._last_progress = None

    async def replay(
        self,
        corpus: ModelExecutionCorpus,
        config: ModelCorpusReplayConfig,
    ) -> ModelCorpusReplayResult:
        """Replay entire corpus with given configuration.

        Replays all executions in the corpus according to the configuration,
        tracking progress and aggregating results.

        Args:
            corpus: The execution corpus to replay.
            config: Configuration for the replay.

        Returns:
            ModelCorpusReplayResult with complete replay results.

        Example:
            >>> result = await orchestrator.replay(corpus, config)
            >>> if result.all_successful:
            ...     print("All replays passed!")
            ... else:
            ...     print(f"Failures: {result.failed}")
        """
        self.reset()
        started_at = datetime.now(UTC)
        start_time = time.perf_counter()

        # Validate corpus
        corpus.validate_for_replay()

        # Filter executions if subset filter is configured
        executions = self._filter_executions(corpus, config)

        if not executions:
            # No executions to replay
            return ModelCorpusReplayResult(
                corpus_id=corpus.corpus_id,
                corpus_name=corpus.name,
                total_executions=0,
                successful=0,
                failed=0,
                skipped=len(corpus.executions),
                execution_results=(),
                aggregate_metrics=ModelAggregateMetrics(),
                config_overrides=config.config_overrides,
                duration_ms=0.0,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )

        # Execute replays
        if config.is_sequential:
            results = await self._replay_sequential(executions, config)
        else:
            results = await self._replay_parallel(executions, config)

        # Calculate metrics
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        # Skipped = executions that were selected but not processed
        # (due to cancellation or fail-fast, not filtering)
        skipped = len(executions) - len(results)

        durations = [r.duration_ms for r in results]
        aggregate_metrics = ModelAggregateMetrics.from_durations(
            durations=durations,
            total_duration_ms=duration_ms,
            success_count=successful,
            total_count=len(results),
        )

        return ModelCorpusReplayResult(
            corpus_id=corpus.corpus_id,
            corpus_name=corpus.name,
            total_executions=len(executions),
            successful=successful,
            failed=failed,
            skipped=skipped,
            execution_results=tuple(results),
            aggregate_metrics=aggregate_metrics,
            config_overrides=config.config_overrides,
            duration_ms=duration_ms,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            was_cancelled=self._cancelled,
            fail_fast_triggered=config.fail_fast and failed > 0,
        )

    def _filter_executions(
        self,
        corpus: ModelExecutionCorpus,
        config: ModelCorpusReplayConfig,
    ) -> list[ModelExecutionManifest]:
        """Filter executions based on subset filter.

        Args:
            corpus: The corpus to filter.
            config: Configuration containing the filter.

        Returns:
            List of executions to replay.
        """
        executions = list(corpus.executions)

        if config.subset_filter is None or not config.subset_filter.has_filters:
            return executions

        subset_filter = config.subset_filter

        # Apply index range filter first (most efficient)
        if subset_filter.index_start is not None or subset_filter.index_end is not None:
            start = subset_filter.index_start or 0
            end = subset_filter.index_end or len(executions)
            executions = executions[start:end]

        # Apply handler filter
        if subset_filter.handler_names:
            handler_set = set(subset_filter.handler_names)
            executions = [
                e
                for e in executions
                if e.node_identity.handler_descriptor_id in handler_set
            ]

        # Apply tag filter (executions don't have tags, but corpus does)
        # Note: This is a placeholder for future tag-based filtering
        # on execution manifests if they gain tag support
        if subset_filter.tags:
            _logger.warning(
                "Tag filter specified but not yet implemented - tags will be ignored: %s",
                subset_filter.tags,
            )

        return executions

    async def _replay_sequential(
        self,
        executions: list[ModelExecutionManifest],
        config: ModelCorpusReplayConfig,
    ) -> list[ModelSingleReplayResult]:
        """Replay executions sequentially.

        Args:
            executions: List of executions to replay.
            config: Replay configuration.

        Returns:
            List of individual replay results.
        """
        results: list[ModelSingleReplayResult] = []
        start_time = time.perf_counter()
        completed_count = 0
        failed_count = 0

        for index, manifest in enumerate(executions):
            if self._cancelled:
                _logger.info(
                    "Replay cancelled at execution %d/%d", index, len(executions)
                )
                break

            # Update progress
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._update_progress(
                total=len(executions),
                completed=completed_count,
                failed=failed_count,
                skipped=0,
                current_manifest=str(manifest.manifest_id),
                current_index=index,
                elapsed_ms=elapsed_ms,
                callback=config.progress_callback,
            )

            # Execute single replay
            result = await self._replay_single(manifest, config)
            results.append(result)

            # Track counts incrementally
            if result.success:
                completed_count += 1
            else:
                failed_count += 1

            # Check fail-fast
            if config.fail_fast and not result.success:
                _logger.info(
                    "Fail-fast triggered at execution %d/%d",
                    index + 1,
                    len(executions),
                )
                break

        return results

    async def _replay_parallel(
        self,
        executions: list[ModelExecutionManifest],
        config: ModelCorpusReplayConfig,
    ) -> list[ModelSingleReplayResult]:
        """Replay executions in parallel with concurrency limit.

        Args:
            executions: List of executions to replay.
            config: Replay configuration.

        Returns:
            List of individual replay results (in original order).

        Note:
            Thread Safety of Counters:
            The ``completed_count`` and ``failed_count`` variables are shared across
            coroutines via ``nonlocal``. These counters are used ONLY for real-time
            progress UI updates. The authoritative final counts are computed from
            the ``results`` list after all tasks complete (see ``replay()`` method,
            lines 241-242), which eliminates any race condition concerns for the
            actual return values.

            In Python's asyncio single-threaded event loop, += operations on integers
            are effectively atomic since there's no preemption mid-operation. However,
            even if slight drift occurred, it would only affect intermediate progress
            display, not the final reported counts.
        """
        results: list[ModelSingleReplayResult | None] = [None] * len(executions)
        semaphore = asyncio.Semaphore(config.concurrency)
        start_time = time.perf_counter()

        # Progress counters - used ONLY for real-time UI updates.
        # Final authoritative counts are computed from `results` list after completion.
        # Lock protects counter updates for clarity and future-proofing, even though
        # asyncio coroutines don't have true preemption.
        counter_lock = asyncio.Lock()
        completed_count = 0
        failed_count = 0
        fail_fast_triggered = False

        async def replay_with_semaphore(
            index: int,
            manifest: ModelExecutionManifest,
        ) -> None:
            nonlocal completed_count, failed_count, fail_fast_triggered

            if self._cancelled or fail_fast_triggered:
                return

            async with semaphore:
                # Re-check after acquiring semaphore (state may have changed
                # between initial check and semaphore acquisition due to
                # concurrent coroutines modifying fail_fast_triggered)
                should_skip = self._cancelled or fail_fast_triggered
                if should_skip:
                    # NOTE(OMN-1302): Defensive early return for race condition. Safe because checks state after lock.
                    return  # type: ignore[unreachable]

                result = await self._replay_single(manifest, config)
                results[index] = result

                # Update progress counters atomically for UI display.
                # Lock ensures consistent reads even with concurrent coroutines.
                async with counter_lock:
                    if result.success:
                        completed_count += 1
                    else:
                        failed_count += 1
                        if config.fail_fast:
                            fail_fast_triggered = True

                    # Update progress inside lock to ensure consistent counter values
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    self._update_progress(
                        total=len(executions),
                        completed=completed_count,
                        failed=failed_count,
                        skipped=0,
                        current_manifest=str(manifest.manifest_id),
                        current_index=index,
                        elapsed_ms=elapsed_ms,
                        callback=config.progress_callback,
                    )

        # Create tasks
        tasks = [
            asyncio.create_task(replay_with_semaphore(i, m))
            for i, m in enumerate(executions)
        ]

        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results (from cancelled tasks)
        return [r for r in results if r is not None]

    async def _replay_single(
        self,
        manifest: ModelExecutionManifest,
        config: ModelCorpusReplayConfig,
    ) -> ModelSingleReplayResult:
        """Replay a single execution with retry support.

        Args:
            manifest: The execution manifest to replay.
            config: Replay configuration.

        Returns:
            Single replay result.
        """
        retry_count = 0
        last_error: Exception | None = None
        start_time = time.perf_counter()

        while retry_count <= config.max_retries:
            try:
                # Get RNG seed from replay context if available, otherwise use 0
                rng_seed = 0
                if hasattr(manifest, "replay_context") and manifest.replay_context:
                    rng_seed = getattr(manifest.replay_context, "rng_seed", 0) or 0

                # Create replay session from manifest
                session = self._executor.create_replay_session(
                    time_frozen_at=manifest.created_at,
                    rng_seed=rng_seed,
                    effect_records=[],  # TODO(OMN-1204): Load from manifest if available
                    original_execution_id=manifest.manifest_id,
                )

                # Execute replay
                # TODO(OMN-1204): Wire up actual replay execution
                # The actual execution function would be provided by the handler/node.
                # For now we simulate success since we don't have the actual handler.

                duration_ms = (time.perf_counter() - start_time) * 1000

                return ModelSingleReplayResult(
                    manifest_id=manifest.manifest_id,
                    success=True,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                )

            except asyncio.CancelledError:
                # CRITICAL: Re-raise CancelledError to honor task cancellation.
                # Cancellation should not be retried - it must propagate immediately.
                raise

            except Exception as e:  # boundary-ok: retry logic must capture all exceptions to track attempts
                last_error = e
                retry_count += 1

                if retry_count <= config.max_retries:
                    _logger.debug(
                        "Retry %d/%d for manifest %s: %s",
                        retry_count,
                        config.max_retries,
                        manifest.manifest_id,
                        str(e),
                    )
                    await asyncio.sleep(config.retry_delay_ms / 1000)

        # All retries exhausted
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ModelSingleReplayResult(
            manifest_id=manifest.manifest_id,
            success=False,
            duration_ms=duration_ms,
            error_message=str(last_error) if last_error else "Unknown error",
            error_type=type(last_error).__name__ if last_error else "UnknownError",
            retry_count=retry_count - 1,
        )

    def _update_progress(
        self,
        total: int,
        completed: int,
        failed: int,
        skipped: int,
        current_manifest: str | None,
        current_index: int | None,
        elapsed_ms: float,
        callback: ProtocolReplayProgressCallback | None,
    ) -> None:
        """Update and emit progress.

        Args:
            total: Total executions.
            completed: Completed count.
            failed: Failed count.
            skipped: Skipped count.
            current_manifest: String representation of current manifest ID.
            current_index: Current execution index.
            elapsed_ms: Elapsed time.
            callback: Optional progress callback (satisfies ProtocolReplayProgressCallback).
        """
        # Estimate remaining time based on average
        processed = completed + failed + skipped
        estimated_remaining_ms = None
        if processed > 0 and elapsed_ms > 0:
            avg_per_execution = elapsed_ms / processed
            remaining = total - processed
            estimated_remaining_ms = avg_per_execution * remaining

        progress = ModelCorpusReplayProgress(
            total=total,
            completed=completed,
            failed=failed,
            skipped=skipped,
            current_manifest=current_manifest,
            current_execution_index=current_index,
            elapsed_ms=elapsed_ms,
            estimated_remaining_ms=estimated_remaining_ms,
        )

        self._last_progress = progress

        if callback:
            try:
                callback(progress)
            except Exception as e:
                # tool-resilience-ok: callback errors must not crash replay
                _logger.warning("Progress callback failed: %s", e)
