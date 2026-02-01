"""
ExecutorReplay - Replay executor for deterministic pipeline replay.

This module provides the ExecutorReplay class that orchestrates deterministic
replay by injecting controlled time, seeded RNG, and recorded effects.

Design:
    The executor creates ReplaySession instances configured for different modes:
    - Production: Normal execution with live time/RNG/effects
    - Recording: Execute normally while capturing all non-determinism
    - Replaying: Replay using captured data for deterministic execution

Architecture:
    ExecutorReplay coordinates the three injector/recorder components:
    - ServiceTimeInjector: Provides fixed or current time
    - ServiceRNGInjector: Provides seeded random numbers
    - ServiceEffectRecorder: Records or replays effect results

Usage:
    .. code-block:: python

        from omnibase_core.pipeline.replay import ExecutorReplay

        # Create executor
        executor = ExecutorReplay()

        # Create recording session
        session = executor.create_recording_session(rng_seed=42)

        # Execute functions with recording
        result = await executor.execute_async(session, my_function, arg1, arg2)

        # Capture manifest for later replay
        manifest = executor.capture_manifest(session)

        # Create replay session from manifest
        from datetime import datetime
        replay_session = executor.create_replay_session(
            time_frozen_at=datetime.fromisoformat(manifest["time_frozen_at"]),
            rng_seed=manifest["rng_seed"],
            effect_records=effect_records_from_manifest,
        )

        # Execute replay
        replay_result = await executor.execute_async(
            replay_session, my_function, arg1, arg2
        )
        assert result == replay_result  # Deterministic!

Key Invariant:
    Same inputs + recorded non-determinism = Same outputs

    .. code-block:: python

        manifest_1 = await executor.execute_async(session1, node.handle, envelope)
        manifest_2 = await executor.execute_async(session2, node.handle, envelope)
        # Where session1 recording was used to create session2 replay
        assert manifest_1 == manifest_2  # Deterministic!

Thread Safety:
    ExecutorReplay instances are stateless and thread-safe.
    ReplaySession instances are NOT thread-safe - use separate sessions per thread.

Related:
    - OMN-1116: Implement Replay Executor for Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7: Replay Infrastructure
    - ServiceTimeInjector: Time injection
    - ServiceRNGInjector: RNG injection
    - ServiceEffectRecorder: Effect recording and replay

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ExecutorReplay"]

import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TypeVar
from uuid import UUID

_logger = logging.getLogger(__name__)

from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.models.replay.model_replay_context import ModelReplayContext
from omnibase_core.pipeline.replay.runner_replay_session import ReplaySession
from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector
from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
from omnibase_core.types.type_json import JsonType

T = TypeVar("T")


class ExecutorReplay:
    """Replay executor for deterministic pipeline replay.

    Orchestrates replay by:
    1. Configuring time injection (fixed time for replay)
    2. Configuring RNG injection (seeded random for replay)
    3. Configuring effect recording/stubbing
    4. Executing functions with deterministic context

    The executor is stateless and thread-safe. Each session it creates
    is independent and configured for a specific replay mode.

    Usage:
        >>> executor = ExecutorReplay()
        >>>
        >>> # Recording mode
        >>> session = executor.create_recording_session()
        >>> result = await executor.execute_async(session, my_function, arg1)
        >>> manifest = executor.capture_manifest(session)
        >>>
        >>> # Replay mode
        >>> replay_session = executor.create_replay_session(
        ...     time_frozen_at=datetime.fromisoformat(manifest["time_frozen_at"]),
        ...     rng_seed=manifest["rng_seed"],
        ...     effect_records=effect_records,
        ... )
        >>> replay_result = await executor.execute_async(
        ...     replay_session, my_function, arg1
        ... )
        >>> assert result == replay_result  # Deterministic!

    Thread Safety:
        ExecutorReplay is stateless and thread-safe. Create separate sessions
        per thread for concurrent execution.

    .. versionadded:: 0.4.0
    """

    def create_production_session(self) -> ReplaySession:
        """Create session for normal production execution.

        Production sessions use live time, random RNG seeds, and pass-through
        effect recording (no recording or replay).

        Returns:
            ReplaySession: Session configured for production mode.

        Example:
            >>> executor = ExecutorReplay()
            >>> session = executor.create_production_session()
            >>> session.mode
            <EnumReplayMode.PRODUCTION: 'production'>
        """
        return ReplaySession(
            context=ModelReplayContext(
                mode=EnumReplayMode.PRODUCTION,
                time_frozen_at=None,
                rng_seed=None,
                original_execution_id=None,
            ),
            time_service=ServiceTimeInjector(),
            rng_service=ServiceRNGInjector(),
            effect_recorder=ServiceEffectRecorder(mode=EnumRecorderMode.PASS_THROUGH),
        )

    def create_recording_session(
        self,
        rng_seed: int | None = None,
    ) -> ReplaySession:
        """Create session for recording execution.

        Recording sessions capture all non-determinism (time, RNG, effects)
        for later replay. The RNG seed is stored in the context for manifest
        capture.

        Args:
            rng_seed: Optional seed for deterministic RNG. If None, a secure
                random seed is auto-generated.

        Returns:
            ReplaySession: Session configured for recording mode.

        Example:
            >>> executor = ExecutorReplay()
            >>> session = executor.create_recording_session(rng_seed=42)
            >>> session.rng_service.seed
            42
            >>> session.effect_recorder.is_recording
            True
        """
        rng = ServiceRNGInjector(seed=rng_seed)
        time_svc = ServiceTimeInjector()
        return ReplaySession(
            context=ModelReplayContext(
                mode=EnumReplayMode.RECORDING,
                time_frozen_at=None,
                rng_seed=rng.seed,
                original_execution_id=None,
            ),
            time_service=time_svc,
            rng_service=rng,
            effect_recorder=ServiceEffectRecorder(
                mode=EnumRecorderMode.RECORDING,
                time_service=time_svc,
            ),
        )

    def create_replay_session(
        self,
        time_frozen_at: datetime,
        rng_seed: int,
        effect_records: list[ModelEffectRecord],
        original_execution_id: UUID | None = None,
    ) -> ReplaySession:
        """Create session for replaying from recorded data.

        Replay sessions use frozen time, seeded RNG, and recorded effect
        results to produce deterministic execution.

        Args:
            time_frozen_at: Fixed time to use for all time queries.
            rng_seed: Seed for deterministic random numbers.
            effect_records: Pre-recorded effect records for replay.
            original_execution_id: Optional ID of the original execution
                being replayed. Stored in context for correlation.

        Returns:
            ReplaySession: Session configured for replay mode.

        Example:
            >>> executor = ExecutorReplay()
            >>> session = executor.create_replay_session(
            ...     time_frozen_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
            ...     rng_seed=42,
            ...     effect_records=[],
            ... )
            >>> session.time_service.now()
            datetime.datetime(2024, 6, 15, 0, 0, tzinfo=datetime.timezone.utc)
        """
        return ReplaySession(
            context=ModelReplayContext(
                mode=EnumReplayMode.REPLAYING,
                time_frozen_at=time_frozen_at,
                rng_seed=rng_seed,
                original_execution_id=original_execution_id,
            ),
            time_service=ServiceTimeInjector(fixed_time=time_frozen_at),
            rng_service=ServiceRNGInjector(seed=rng_seed),
            effect_recorder=ServiceEffectRecorder(
                mode=EnumRecorderMode.REPLAYING,
                records=effect_records,
            ),
        )

    def capture_manifest(self, session: ReplaySession) -> dict[str, JsonType]:
        """Capture replay manifest from recording session.

        Captures all data needed to replay an execution:
        - session_id: Unique session identifier
        - time_frozen_at: Time to use for replay (ISO format)
        - rng_seed: RNG seed for deterministic random numbers
        - effect_records: List of effect record dicts

        The returned manifest is JSON-serializable for storage.

        Args:
            session: Recording session to capture manifest from.

        Returns:
            dict[str, JsonType]: Replay manifest with all determinism data.

        Example:
            >>> session = executor.create_recording_session(rng_seed=42)
            >>> session.effect_recorder.record("http.get", {"url": "..."}, {"status": 200})
            >>> manifest = executor.capture_manifest(session)
            >>> manifest["rng_seed"]
            42
            >>> len(manifest["effect_records"])
            1
        """
        # Use iter_records() to avoid creating a copy of the records list
        return {
            "session_id": str(session.session_id),
            "time_frozen_at": session.time_service.now().isoformat(),
            "rng_seed": session.rng_service.seed,
            "effect_records": [
                record.model_dump(mode="json")
                for record in session.effect_recorder.iter_records()
            ],
        }

    async def execute_async(
        self,
        session: ReplaySession,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute async function with replay context.

        If the function has a parameter named 'replay_session', the session
        is automatically injected as a keyword argument.

        Args:
            session: Replay session providing time/RNG/effect services.
            func: Async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            T: Result from the function execution.

        Warning:
            If you include 'replay_session' in kwargs, it will be **overwritten**
            by the executor's session parameter. This is intentional: the executor
            manages session lifecycle, so always pass the session to execute_async()
            rather than including it in kwargs. A warning is logged if this occurs.

        Example:
            >>> async def my_func(replay_session):
            ...     return replay_session.rng_service.random()
            >>> result = await executor.execute_async(session, my_func)
        """
        # Check if function expects replay_session parameter
        sig = inspect.signature(func)
        if "replay_session" in sig.parameters:
            # Warn if user provided replay_session in kwargs, as we will overwrite it.
            # This is intentional (executor manages session lifecycle) but could be confusing.
            if "replay_session" in kwargs:
                _logger.warning(
                    "User-provided 'replay_session' in kwargs will be overwritten by "
                    "ExecutorReplay. The executor manages session lifecycle; pass the "
                    "session to execute_async() instead of including it in kwargs."
                )
            kwargs["replay_session"] = session
        return await func(*args, **kwargs)

    def execute_sync(
        self,
        session: ReplaySession,
        func: Callable[..., T],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute sync function with replay context.

        If the function has a parameter named 'replay_session', the session
        is automatically injected as a keyword argument.

        Args:
            session: Replay session providing time/RNG/effect services.
            func: Sync function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            T: Result from the function execution.

        Warning:
            If you include 'replay_session' in kwargs, it will be **overwritten**
            by the executor's session parameter. This is intentional: the executor
            manages session lifecycle, so always pass the session to execute_sync()
            rather than including it in kwargs. A warning is logged if this occurs.

        Example:
            >>> def my_func(replay_session):
            ...     return replay_session.time_service.now()
            >>> result = executor.execute_sync(session, my_func)
        """
        # Check if function expects replay_session parameter
        sig = inspect.signature(func)
        if "replay_session" in sig.parameters:
            # Warn if user provided replay_session in kwargs, as we will overwrite it.
            # This is intentional (executor manages session lifecycle) but could be confusing.
            if "replay_session" in kwargs:
                _logger.warning(
                    "User-provided 'replay_session' in kwargs will be overwritten by "
                    "ExecutorReplay. The executor manages session lifecycle; pass the "
                    "session to execute_sync() instead of including it in kwargs."
                )
            kwargs["replay_session"] = session
        return func(*args, **kwargs)
