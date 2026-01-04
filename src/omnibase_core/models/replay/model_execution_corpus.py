# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Execution Corpus Model for Replay Testing.

Defines ModelExecutionCorpus for curated collections of execution manifests
used for systematic testing and comparison.

A corpus is a collection of 20-50+ real production requests that enables:

- **Regression Testing**: Verify system behavior matches baseline
- **Performance Comparison**: Compare execution times across versions
- **Handler Coverage**: Ensure all handlers are exercised
- **A/B Testing**: Compare different implementations on same inputs

Design:
    ModelExecutionCorpus supports two modes of operation:

    - **Materialized**: Full execution manifests stored inline (executions tuple)
    - **Reference**: Only manifest IDs stored (execution_ids tuple)

    The materialized mode is useful for self-contained test fixtures, while
    reference mode is better for large corpora where manifests are stored
    separately in a database or file system.

Architecture:
    ::

        ModelExecutionCorpus
            |
            +-- executions: tuple[ModelExecutionManifest, ...]  # Materialized
            |
            +-- execution_ids: tuple[UUID, ...]                 # Reference mode
            |
            +-- get_statistics() -> ModelCorpusStatistics       # Method

Thread Safety:
    ModelExecutionCorpus is frozen (immutable) after creation, making it
    safe to share across threads. The `with_execution` method returns a
    new instance rather than mutating in place.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelExecutionCorpus
        from omnibase_core.models.manifest import ModelExecutionManifest

        # Create a corpus
        corpus = ModelExecutionCorpus(
            name="production-sample-2024q4",
            version="1.0.0",
            source="production",
            description="Q4 2024 production request sample",
        )

        # Add executions (returns new instance since frozen)
        corpus = corpus.with_execution(manifest1)
        corpus = corpus.with_execution(manifest2)

        # Access statistics
        stats = corpus.get_statistics()
        print(f"Total: {stats.total_executions}")
        print(f"Success rate: {stats.success_rate:.1%}")

        # Query by handler
        transform_runs = corpus.get_executions_by_handler("text-transform")

Related:
    - OMN-1202: Execution Corpus Model for beta demo
    - ModelExecutionManifest: Individual execution records
    - ModelReplayContext: Determinism context for replay

.. versionadded:: 0.4.0
"""

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.replay.model_corpus_capture_window import (
    ModelCorpusCaptureWindow,
)
from omnibase_core.models.replay.model_corpus_statistics import ModelCorpusStatistics
from omnibase_core.models.replay.model_corpus_time_range import ModelCorpusTimeRange


class ModelExecutionCorpus(BaseModel):
    """
    Collection of execution manifests for replay testing.

    A corpus is a curated collection of 20-50+ real production requests
    used for systematic testing and comparison. It supports both materialized
    (inline manifests) and reference (IDs only) modes.

    Attributes:
        corpus_id: Unique identifier for this corpus.
        name: Human-readable name for the corpus.
        version: Semantic version string of the corpus.
        source: Source environment (e.g., "production", "staging", "synthetic").
        description: Optional description of the corpus.
        tags: Optional tags for categorization.
        capture_window: Optional time range for when executions were captured.
        executions: Materialized tuple of execution manifests.
        execution_ids: Reference mode tuple of manifest IDs.
        is_reference: Whether corpus is in reference mode.
        created_at: When the corpus was created.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads. The `with_execution` method returns a new
        instance rather than mutating in place.

    Example:
        Create and populate a corpus::

            corpus = ModelExecutionCorpus(
                name="regression-suite-v1",
                version="1.0.0",
                source="production",
                description="Regression test corpus from production",
            )

            # Add executions (returns new instance)
            corpus = corpus.with_execution(manifest1)
            corpus = corpus.with_execution(manifest2)

            # Check statistics
            stats = corpus.get_statistics()
            print(f"Success rate: {stats.success_rate:.1%}")

        Query by handler::

            transform_runs = corpus.get_executions_by_handler("text-transform")
            for manifest in transform_runs:
                print(f"  {manifest.manifest_id}: {manifest.get_total_duration_ms()}ms")

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          Individual execution record model
        - :class:`~omnibase_core.models.replay.model_replay_context.ModelReplayContext`:
          Determinism context for replay execution

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # === Identity ===

    corpus_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this corpus",
    )

    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the corpus",
    )

    version: str = Field(
        ...,
        min_length=1,
        description="Semantic version string of the corpus (e.g., '1.0.0')",
    )

    source: str = Field(
        ...,
        min_length=1,
        description="Source environment (e.g., 'production', 'staging', 'synthetic')",
    )

    description: str | None = Field(
        default=None,
        description="Optional description of the corpus",
    )

    tags: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Optional tags for categorization",
    )

    # === Time Range ===

    capture_window: ModelCorpusCaptureWindow | None = Field(
        default=None,
        description="Time range for when executions were captured",
    )

    # === Executions ===

    executions: tuple[ModelExecutionManifest, ...] = Field(
        default_factory=tuple,
        description="Materialized tuple of execution manifests",
    )

    execution_ids: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Reference mode tuple of manifest IDs (stored separately)",
    )

    is_reference: bool = Field(
        default=False,
        description="Whether corpus is in reference mode",
    )

    # === Timestamps ===

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the corpus was created",
    )

    # === Validators ===

    @model_validator(mode="after")
    def _validate_mode_consistency(self) -> "ModelExecutionCorpus":
        """Validate that is_reference flag matches the data state.

        A reference-mode corpus should have execution_ids but no executions.
        A materialized corpus should have executions and optionally execution_ids
        for mixed mode.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If mode is inconsistent with data.
        """
        has_executions = len(self.executions) > 0
        has_refs = len(self.execution_ids) > 0

        # Reference mode should not have materialized executions
        if self.is_reference and has_executions:
            msg = (
                "Reference mode corpus should not have materialized executions. "
                f"Found {len(self.executions)} executions with is_reference=True."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # If only has refs and no executions, is_reference should be True
        if has_refs and not has_executions and not self.is_reference:
            msg = (
                "Corpus with only execution_ids should have is_reference=True. "
                f"Found {len(self.execution_ids)} refs with is_reference=False."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return self

    # === Properties ===

    @property
    def is_materialized(self) -> bool:
        """
        Check if corpus is in materialized mode.

        Returns:
            True if not in reference mode.
        """
        return not self.is_reference

    @property
    def is_valid_for_replay(self) -> bool:
        """
        Check if corpus is valid for replay.

        Checks both materialized executions and reference execution_ids,
        consistent with validate_for_replay() method.

        Returns:
            True if corpus has at least one execution (materialized or reference).
        """
        return self.execution_count > 0

    @property
    def execution_count(self) -> int:
        """
        Get total execution count (materialized + refs).

        Returns:
            Total count of executions in both modes.
        """
        return len(self.executions) + len(self.execution_ids)

    # === Methods ===

    def get_statistics(self) -> ModelCorpusStatistics:
        """
        Calculate statistics from current executions.

        Computes handler distribution, success rate, and
        average duration from the materialized execution manifests.

        Returns:
            ModelCorpusStatistics with computed values.

        Note:
            Statistics are computed only from materialized executions in the
            ``executions`` tuple. Reference-mode execution_ids are not included
            since their manifests are stored externally.

            When called on a reference-only corpus (executions tuple empty),
            returns an empty ModelCorpusStatistics with all zero values. To get
            meaningful statistics for reference-mode corpora, first resolve the
            execution_ids to full manifests using your storage system.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test",
            ...     executions=(manifest1, manifest2),
            ... )
            >>> stats = corpus.get_statistics()
            >>> stats.total_executions
            2
        """
        total = len(self.executions)

        if total == 0:
            # Early return prevents division by zero in success_rate and avg_duration
            return ModelCorpusStatistics()

        # Handler distribution - count by handler_descriptor_id
        handler_counts: Counter[str] = Counter()
        for manifest in self.executions:
            handler_id = manifest.node_identity.handler_descriptor_id
            if handler_id:
                handler_counts[handler_id] += 1

        # Success/failure counts
        successful = sum(1 for m in self.executions if m.is_successful())
        failed = total - successful
        success_rate = successful / total

        # Average duration
        durations = [m.get_total_duration_ms() for m in self.executions]
        avg_duration = sum(durations) / total

        return ModelCorpusStatistics(
            total_executions=total,
            success_count=successful,
            failure_count=failed,
            handler_distribution=dict(handler_counts),
            success_rate=success_rate,
            avg_duration_ms=avg_duration,
        )

    def get_time_range(self) -> ModelCorpusTimeRange | None:
        """
        Get the time range of executions in the corpus.

        Returns:
            ModelCorpusTimeRange with min/max times, or None if empty.

        Example:
            >>> time_range = corpus.get_time_range()
            >>> if time_range:
            ...     print(f"Duration: {time_range.duration}")
        """
        if not self.executions:
            return None

        created_times = [m.created_at for m in self.executions]
        return ModelCorpusTimeRange(
            min_time=min(created_times),
            max_time=max(created_times),
        )

    def with_execution(
        self, manifest: ModelExecutionManifest
    ) -> "ModelExecutionCorpus":
        """
        Add an execution manifest to the corpus.

        Creates a new corpus instance with the manifest appended to the
        executions tuple. The original corpus is not modified (frozen model).

        Args:
            manifest: The execution manifest to add.

        Returns:
            A new ModelExecutionCorpus with the manifest added.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test"
            ... )
            >>> corpus = corpus.with_execution(manifest)
            >>> len(corpus.executions)
            1

        Note:
            For large corpora (1000+ executions), prefer using ``with_executions()``
            to add multiple manifests in a single operation, as this avoids
            repeated tuple copying that occurs when calling ``with_execution()``
            in a loop.
        """
        return self.model_copy(
            update={
                "executions": (*self.executions, manifest),
            }
        )

    def with_executions(
        self,
        manifests: tuple[ModelExecutionManifest, ...] | list[ModelExecutionManifest],
    ) -> "ModelExecutionCorpus":
        """
        Add multiple execution manifests to the corpus.

        Creates a new corpus instance with the manifests appended to the
        executions tuple. The original corpus is not modified (frozen model).

        Args:
            manifests: The execution manifests to add.

        Returns:
            A new ModelExecutionCorpus with the manifests added.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test"
            ... )
            >>> corpus = corpus.with_executions([manifest1, manifest2])
            >>> len(corpus.executions)
            2
        """
        return self.model_copy(
            update={
                "executions": (*self.executions, *manifests),
            }
        )

    def with_execution_ref(self, manifest_id: UUID) -> "ModelExecutionCorpus":
        """
        Add an execution reference to the corpus.

        Creates a new corpus instance with the manifest ID appended to the
        execution_ids tuple. The original corpus is not modified (frozen model).

        Args:
            manifest_id: The UUID of the execution manifest to reference.

        Returns:
            A new ModelExecutionCorpus with the reference added.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test"
            ... )
            >>> corpus = corpus.with_execution_ref(uuid4())
            >>> len(corpus.execution_ids)
            1

        Note:
            For large corpora, prefer using ``with_execution_refs()`` to add
            multiple references in a single operation.
        """
        return self.model_copy(
            update={
                "execution_ids": (*self.execution_ids, manifest_id),
            }
        )

    def with_execution_refs(
        self, manifest_ids: tuple[UUID, ...] | list[UUID]
    ) -> "ModelExecutionCorpus":
        """
        Add multiple execution references to the corpus.

        Creates a new corpus instance with the manifest IDs appended to the
        execution_ids tuple. The original corpus is not modified (frozen model).

        Args:
            manifest_ids: The UUIDs of execution manifests to reference.

        Returns:
            A new ModelExecutionCorpus with the references added.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test"
            ... )
            >>> corpus = corpus.with_execution_refs([uuid4(), uuid4()])
            >>> len(corpus.execution_ids)
            2
        """
        return self.model_copy(
            update={
                "execution_ids": (*self.execution_ids, *manifest_ids),
            }
        )

    def validate_for_replay(self) -> None:
        """
        Validate that corpus is ready for replay.

        Checks that:
        - Corpus has at least one execution (materialized or ref)
        - All materialized executions have valid manifests

        Raises:
            ModelOnexError: If corpus is empty or contains invalid manifests.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test"
            ... )
            >>> corpus.validate_for_replay()  # Raises ModelOnexError
            Traceback (most recent call last):
                ...
            ModelOnexError: Corpus is empty...
        """
        if self.execution_count == 0:
            msg = (
                f"Corpus '{self.name}' is empty. "
                "Add at least one execution or execution_id before replay."
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Validate materialized manifests have non-empty node_id
        # Note: node_identity and contract_identity are required fields in
        # ModelExecutionManifest, so we only need to validate their contents
        for i, manifest in enumerate(self.executions):
            if not manifest.node_identity.node_id:
                msg = f"Execution {i} in corpus '{self.name}' has empty node_id"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if not manifest.contract_identity.contract_id:
                msg = f"Execution {i} in corpus '{self.name}' has empty contract_id"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        # Validate reference mode execution_ids contain valid (non-nil) UUIDs
        nil_uuid = UUID(int=0)
        for i, exec_id in enumerate(self.execution_ids):
            if exec_id == nil_uuid:
                msg = f"Execution reference {i} in corpus '{self.name}' is nil UUID"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

    def get_executions_by_handler(
        self, handler_name: str
    ) -> tuple[ModelExecutionManifest, ...]:
        """
        Query executions by handler name.

        Filters the materialized executions to return only those matching
        the specified handler_descriptor_id.

        Args:
            handler_name: The handler_descriptor_id to filter by.

        Returns:
            Tuple of matching execution manifests.

        Example:
            >>> corpus = ModelExecutionCorpus(
            ...     name="test", version="1.0.0", source="test",
            ...     executions=(manifest1, manifest2),
            ... )
            >>> transforms = corpus.get_executions_by_handler("text-transform")
            >>> len(transforms)
            1
        """
        return tuple(
            m
            for m in self.executions
            if m.node_identity.handler_descriptor_id == handler_name
        )

    def get_successful_executions(self) -> tuple[ModelExecutionManifest, ...]:
        """
        Get all successful executions.

        Returns:
            Tuple of execution manifests where is_successful() is True.
        """
        return tuple(m for m in self.executions if m.is_successful())

    def get_failed_executions(self) -> tuple[ModelExecutionManifest, ...]:
        """
        Get all failed executions.

        Returns:
            Tuple of execution manifests where is_successful() is False.
        """
        return tuple(m for m in self.executions if not m.is_successful())

    def get_unique_handlers(self) -> tuple[str, ...]:
        """
        Get tuple of unique handler/node IDs in the corpus.

        Returns:
            Sorted tuple of unique handler_descriptor_id values.
        """
        return tuple(
            sorted(
                {
                    m.node_identity.handler_descriptor_id
                    for m in self.executions
                    if m.node_identity.handler_descriptor_id
                }
            )
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        mode = "materialized" if self.is_materialized else "reference"
        return (
            f"ExecutionCorpus('{self.name}' v{self.version}, "
            f"{self.execution_count} executions [{mode}])"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionCorpus(corpus_id={self.corpus_id!r}, "
            f"name={self.name!r}, version={self.version!r}, "
            f"source={self.source!r}, "
            f"executions={len(self.executions)}, "
            f"execution_ids={len(self.execution_ids)})"
        )


# Export for use
__all__ = [
    "ModelExecutionCorpus",
]
