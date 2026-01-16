"""
Execution Manifest Model for Pipeline Observability.

Defines the ModelExecutionManifest model which is the top-level manifest
for a pipeline run. It answers "what ran and why" by capturing all aspects
of execution including node identity, contract identity, capability
activation, ordering, hook traces, emissions, and failures.

This is a pure data model with no side effects. The manifest is fully
JSON-serializable and makes no persistence assumptions.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.manifest.model_activation_summary import (
    ModelActivationSummary,
)
from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_emissions_summary import ModelEmissionsSummary
from omnibase_core.models.manifest.model_hook_trace import ModelHookTrace
from omnibase_core.models.manifest.model_manifest_failure import ModelManifestFailure
from omnibase_core.models.manifest.model_metrics_summary import ModelMetricsSummary
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.models.manifest.model_ordering_summary import ModelOrderingSummary
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExecutionManifest(BaseModel):
    """
    Complete execution manifest for a pipeline run.

    This is the top-level manifest that captures everything about a pipeline
    execution, answering:
    - What ran? (node_identity, contract_identity)
    - Why did it run? (activation_summary)
    - In what order? (ordering_summary)
    - What happened? (hook_traces, failures)
    - What was produced? (emissions_summary)
    - How did it perform? (metrics_summary)

    The manifest is designed to be:
    - Fully JSON-serializable
    - Immutable after creation (frozen)
    - Self-contained (no external references required)
    - Deterministic (same inputs produce same structure)

    Attributes:
        manifest_id: Unique identifier for this manifest
        created_at: When the manifest was created
        manifest_version: Schema version of the manifest
        node_identity: Identity of the executing node
        contract_identity: Identity of the driving contract
        activation_summary: Capability activation decisions
        ordering_summary: Resolved execution order
        hook_traces: Per-hook execution traces
        emissions_summary: Summary of outputs produced
        metrics_summary: Optional performance metrics
        failures: List of failures during execution
        correlation_id: Optional correlation ID for distributed tracing
        parent_manifest_id: Parent manifest ID if nested execution

    Example:
        >>> from datetime import UTC, datetime
        >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> manifest = ModelExecutionManifest(
        ...     node_identity=ModelNodeIdentity(
        ...         node_id="compute-001",
        ...         node_kind=EnumNodeKind.COMPUTE,
        ...         node_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     ),
        ...     contract_identity=ModelContractIdentity(contract_id="contract-001"),
        ...     created_at=datetime.now(UTC),  # Explicit UTC timestamp
        ... )
        >>> manifest.is_successful()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_node_identity.ModelNodeIdentity`:
          Node identity model
        - :class:`~omnibase_core.models.manifest.model_contract_identity.ModelContractIdentity`:
          Contract identity model

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Identity ===

    manifest_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this manifest",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the manifest was created (UTC)",
    )

    manifest_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Schema version of the manifest format",
    )

    # === What Was Executing ===

    node_identity: ModelNodeIdentity = Field(
        ...,
        description="Identity of the executing node",
    )

    contract_identity: ModelContractIdentity = Field(
        ...,
        description="Identity of the driving contract",
    )

    # === What Ran and Why ===

    activation_summary: ModelActivationSummary = Field(
        default_factory=ModelActivationSummary,
        description="Capability activation decisions",
    )

    # === Execution Order ===

    ordering_summary: ModelOrderingSummary = Field(
        default_factory=ModelOrderingSummary,
        description="Resolved execution order",
    )

    # === Execution Trace ===

    hook_traces: list[ModelHookTrace] = Field(
        default_factory=list,
        description="Per-hook execution traces",
    )

    # === What Was Produced ===

    emissions_summary: ModelEmissionsSummary = Field(
        default_factory=ModelEmissionsSummary,
        description="Summary of outputs produced",
    )

    # === Optional Sections ===

    metrics_summary: ModelMetricsSummary | None = Field(
        default=None,
        description="Optional performance metrics",
    )

    failures: list[ModelManifestFailure] = Field(
        default_factory=list,
        description="Failures during execution",
    )

    # === Correlation ===

    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for distributed tracing",
    )

    parent_manifest_id: UUID | None = Field(
        default=None,
        description="Parent manifest ID if this is a nested execution",
    )

    # === Utility Methods ===

    def is_successful(self) -> bool:
        """
        Check if the execution was successful.

        Returns:
            True if no failures and all completed hooks succeeded
        """
        if len(self.failures) > 0:
            return False
        # Check all completed hook traces
        for trace in self.hook_traces:
            if trace.is_failure():
                return False
        return True

    def get_failed_hooks(self) -> list[ModelHookTrace]:
        """
        Get all hook traces that failed.

        Returns:
            List of failed hook traces
        """
        return [trace for trace in self.hook_traces if trace.is_failure()]

    def get_successful_hooks(self) -> list[ModelHookTrace]:
        """
        Get all hook traces that succeeded.

        Returns:
            List of successful hook traces
        """
        return [trace for trace in self.hook_traces if trace.is_success()]

    def get_skipped_hooks(self) -> list[ModelHookTrace]:
        """
        Get all hook traces that were skipped.

        Returns:
            List of skipped hook traces
        """
        return [trace for trace in self.hook_traces if trace.is_skipped()]

    def get_hook_count(self) -> int:
        """
        Get the total number of hook traces.

        Returns:
            Count of hook traces
        """
        return len(self.hook_traces)

    def get_failure_count(self) -> int:
        """
        Get the number of failures.

        Returns:
            Count of failures
        """
        return len(self.failures)

    def get_total_duration_ms(self) -> float:
        """
        Get the total execution duration in milliseconds.

        Returns:
            Total duration from metrics if available, otherwise sum of hook durations
        """
        if self.metrics_summary:
            return self.metrics_summary.total_duration_ms
        return sum(trace.duration_ms for trace in self.hook_traces)

    def get_phases_executed(self) -> list[str]:
        """
        Get the list of phases that were executed.

        Returns:
            Ordered list of unique phase names from hook traces
        """
        seen = set()
        phases = []
        for trace in self.hook_traces:
            phase_value = trace.phase.value
            if phase_value not in seen:
                seen.add(phase_value)
                phases.append(phase_value)
        return phases

    def has_failures(self) -> bool:
        """
        Check if there were any failures.

        Returns:
            True if failures list is non-empty
        """
        return len(self.failures) > 0

    def has_metrics(self) -> bool:
        """
        Check if metrics are available.

        Returns:
            True if metrics_summary is set
        """
        return self.metrics_summary is not None

    def is_nested(self) -> bool:
        """
        Check if this is a nested execution.

        Returns:
            True if parent_manifest_id is set
        """
        return self.parent_manifest_id is not None

    def get_manifest_version_string(self) -> str:
        """
        Get the manifest version as a string.

        Returns:
            Version string in format 'major.minor.patch'
        """
        return str(self.manifest_version)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "SUCCESS" if self.is_successful() else "FAILED"
        duration = self.get_total_duration_ms()
        return (
            f"ExecutionManifest({self.node_identity.node_id}: "
            f"{status}, {self.get_hook_count()} hooks, {duration:.1f}ms)"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionManifest(manifest_id={self.manifest_id!r}, "
            f"node_id={self.node_identity.node_id!r}, "
            f"contract_id={self.contract_identity.contract_id!r}, "
            f"hook_count={self.get_hook_count()}, "
            f"failures={self.get_failure_count()})"
        )


# Export for use
__all__ = ["ModelExecutionManifest"]
