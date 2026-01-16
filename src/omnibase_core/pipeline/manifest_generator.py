"""
Manifest Generator for Pipeline Observability.

Provides the ManifestGenerator class which accumulates observations during
pipeline execution and builds immutable execution manifests.

This is the core component for manifest generation - it collects data about
what ran, why it ran, in what order, and what it produced.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import warnings
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_activation_reason import EnumActivationReason
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.manifest.model_activation_summary import (
    ModelActivationSummary,
)
from omnibase_core.models.manifest.model_capability_activation import (
    ModelCapabilityActivation,
)
from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_dependency_edge import ModelDependencyEdge
from omnibase_core.models.manifest.model_emissions_summary import ModelEmissionsSummary
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.manifest.model_hook_trace import ModelHookTrace
from omnibase_core.models.manifest.model_manifest_failure import ModelManifestFailure
from omnibase_core.models.manifest.model_metrics_summary import ModelMetricsSummary
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.models.manifest.model_ordering_summary import ModelOrderingSummary


class ManifestGenerator:
    """
    Accumulates execution observations and generates manifests.

    This class uses a builder/accumulator pattern to collect observations
    during pipeline execution and produce a final immutable manifest.

    The generator tracks:
    - Capability activation decisions (what ran and why)
    - Execution ordering (phases, handlers, dependencies)
    - Hook execution traces (timing, status, errors)
    - Emissions (events, intents, projections, actions)
    - Failures

    Thread Safety:
        This class is NOT thread-safe. Each ManifestGenerator instance should
        be used by a single thread/coroutine at a time.

        **Why not thread-safe**: The generator maintains mutable state (lists and
        dicts) that are modified without synchronization during recording operations.
        Concurrent calls to recording methods (e.g., ``record_capability_activation()``,
        ``start_hook()``, ``complete_hook()``) from multiple threads could result in:

        - Lost updates to accumulator lists
        - Corrupted ``_pending_hooks`` dict state
        - Inconsistent manifest output

        **Intended usage pattern**: Create one ManifestGenerator per pipeline
        execution. The generator accumulates observations throughout a single
        pipeline run and produces one manifest via ``build()``.

        **What IS safe**:

        - Creating multiple ManifestGenerator instances in different threads
        - Passing the built ``ModelExecutionManifest`` (immutable) across threads
        - Calling ``build()`` multiple times from the same thread (returns new
          manifest snapshot each time)

        **If you need concurrent recording**: Create separate ManifestGenerator
        instances for each concurrent execution context, then aggregate the
        resulting manifests at a higher level if needed.

    Example:
        >>> from omnibase_core.pipeline import ManifestGenerator
        >>> from omnibase_core.models.manifest import ModelNodeIdentity, ModelContractIdentity
        >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
        >>> from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
        >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>>
        >>> generator = ManifestGenerator(
        ...     node_identity=ModelNodeIdentity(
        ...         node_id="compute-001",
        ...         node_kind=EnumNodeKind.COMPUTE,
        ...         node_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     ),
        ...     contract_identity=ModelContractIdentity(contract_id="contract-001"),
        ... )
        >>>
        >>> # Record hook execution
        >>> generator.start_hook("hook-1", "handler-1", EnumHandlerExecutionPhase.EXECUTE)
        >>> generator.complete_hook("hook-1", EnumExecutionStatus.SUCCESS)
        >>>
        >>> # Build manifest
        >>> manifest = generator.build()
        >>> manifest.is_successful()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The manifest model produced by this generator
        - :class:`~omnibase_core.pipeline.manifest_observer.ManifestObserver`:
          Integration helper for pipeline context

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    __slots__ = (
        "_actions",
        "_activated_capabilities",
        "_contract_identity",
        "_correlation_id",
        "_dependency_edges",
        "_events",
        "_failures",
        "_hook_traces",
        "_intents",
        "_manifest_id",
        "_node_identity",
        "_on_manifest_built",
        "_ordering_policy",
        "_ordering_rationale",
        "_parent_manifest_id",
        "_pending_hooks",
        "_phase_durations",
        "_phases",
        "_projections",
        "_resolved_order",
        "_skipped_capabilities",
        "_started_at",
    )

    def __init__(
        self,
        node_identity: ModelNodeIdentity,
        contract_identity: ModelContractIdentity,
        correlation_id: UUID | None = None,
        parent_manifest_id: UUID | None = None,
        on_manifest_built: list[Callable[["ModelExecutionManifest"], None]]
        | None = None,
    ) -> None:
        """
        Initialize the manifest generator.

        Args:
            node_identity: Identity of the executing node
            contract_identity: Identity of the driving contract
            correlation_id: Optional correlation ID for distributed tracing
            parent_manifest_id: Parent manifest ID if nested execution
            on_manifest_built: Optional list of callbacks invoked when manifest is built.
                Each callback receives the completed ModelExecutionManifest.
                Callbacks are invoked synchronously after build() completes.
                Exceptions in callbacks are caught and logged as warnings.

        .. versionchanged:: 0.5.0
            Added ``on_manifest_built`` parameter for corpus capture integration (OMN-1203)
        """
        self._manifest_id = uuid4()
        self._started_at = datetime.now(UTC)
        self._node_identity = node_identity
        self._contract_identity = contract_identity
        self._correlation_id = correlation_id
        self._parent_manifest_id = parent_manifest_id
        self._on_manifest_built: list[Callable[[ModelExecutionManifest], None]] = (
            list(on_manifest_built) if on_manifest_built else []
        )

        # Accumulators for activation
        self._activated_capabilities: list[ModelCapabilityActivation] = []
        self._skipped_capabilities: list[ModelCapabilityActivation] = []

        # Accumulators for ordering
        self._phases: list[str] = []
        self._resolved_order: list[str] = []
        self._dependency_edges: list[ModelDependencyEdge] = []
        self._ordering_policy: str | None = None
        self._ordering_rationale: str | None = None

        # Accumulators for execution
        self._hook_traces: list[ModelHookTrace] = []
        self._pending_hooks: dict[str, ModelHookTrace] = {}

        # Accumulators for failures
        self._failures: list[ModelManifestFailure] = []

        # Accumulators for emissions
        self._events: list[str] = []
        self._intents: list[str] = []
        self._projections: list[str] = []
        self._actions: list[str] = []

        # Accumulators for metrics
        self._phase_durations: dict[str, float] = {}

    @property
    def manifest_id(self) -> UUID:
        """Get the manifest ID."""
        return self._manifest_id

    @property
    def started_at(self) -> datetime:
        """Get the start timestamp."""
        return self._started_at

    # === Callback Registration ===

    def register_on_build_callback(
        self,
        callback: Callable[["ModelExecutionManifest"], None],
    ) -> None:
        """
        Register a callback to be invoked when the manifest is built.

        Callbacks are invoked synchronously after ``build()`` creates the manifest.
        Multiple callbacks are invoked in registration order. Exceptions in
        callbacks are caught and logged as warnings (they do not prevent
        subsequent callbacks or the return of the manifest).

        Args:
            callback: A callable that receives the completed ModelExecutionManifest.
                The callback should not modify the manifest (it's frozen/immutable).

        Example:
            >>> def capture_manifest(manifest: ModelExecutionManifest) -> None:
            ...     corpus_service.capture(manifest)
            >>>
            >>> generator.register_on_build_callback(capture_manifest)

        .. versionadded:: 0.5.0
            Added for corpus capture integration (OMN-1203)
        """
        self._on_manifest_built.append(callback)

    # === Activation Recording ===

    @standard_error_handling("Capability activation recording")
    def record_capability_activation(
        self,
        capability_name: str,
        activated: bool,
        reason: EnumActivationReason,
        predicate_expression: str | None = None,
        predicate_result: bool | None = None,
        predicate_inputs: dict[str, str | int | float | bool | None] | None = None,
        dependencies_satisfied: bool = True,
        conflict_with: list[str] | None = None,
    ) -> None:
        """
        Record a capability activation decision.

        Args:
            capability_name: Qualified name of the capability
            activated: Whether the capability was activated
            reason: Why the capability was activated or skipped
            predicate_expression: Optional predicate expression evaluated
            predicate_result: Optional result of predicate evaluation
            predicate_inputs: Optional inputs used for predicate evaluation
            dependencies_satisfied: Whether dependencies were satisfied
            conflict_with: List of conflicting capability names
        """
        activation = ModelCapabilityActivation(
            capability_name=capability_name,
            activated=activated,
            reason=reason,
            predicate_expression=predicate_expression,
            predicate_result=predicate_result,
            predicate_inputs=predicate_inputs,
            dependencies_satisfied=dependencies_satisfied,
            conflict_with=conflict_with or [],
        )

        if activated:
            self._activated_capabilities.append(activation)
        else:
            self._skipped_capabilities.append(activation)

    # === Ordering Recording ===

    @standard_error_handling("Execution ordering recording")
    def record_ordering(
        self,
        phases: list[str],
        resolved_order: list[str],
        dependency_edges: list[ModelDependencyEdge] | None = None,
        ordering_policy: str | None = None,
        ordering_rationale: str | None = None,
    ) -> None:
        """
        Record the resolved execution ordering.

        Args:
            phases: List of phases in execution order
            resolved_order: Handler IDs in resolved execution order
            dependency_edges: Dependency relationships used for ordering
            ordering_policy: Policy used (e.g., 'topological_sort', 'priority')
            ordering_rationale: Human-readable explanation of ordering
        """
        self._phases = phases
        self._resolved_order = resolved_order
        self._dependency_edges = dependency_edges or []
        self._ordering_policy = ordering_policy
        self._ordering_rationale = ordering_rationale

    @standard_error_handling("Dependency edge addition")
    def add_dependency_edge(
        self,
        from_handler_id: str,  # string-id-ok: user-facing handler identifier
        to_handler_id: str,  # string-id-ok: user-facing handler identifier
        dependency_type: str = "requires",
        satisfied: bool = True,
    ) -> None:
        """
        Add a single dependency edge.

        Args:
            from_handler_id: The dependent handler
            to_handler_id: The handler being depended upon
            dependency_type: Type of dependency
            satisfied: Whether the dependency was satisfied
        """
        edge = ModelDependencyEdge(
            from_handler_id=from_handler_id,
            to_handler_id=to_handler_id,
            dependency_type=dependency_type,
            satisfied=satisfied,
        )
        self._dependency_edges.append(edge)

    # === Hook Execution Recording ===

    @standard_error_handling("Hook execution start")
    def start_hook(
        self,
        hook_id: str,  # string-id-ok: user-facing hook identifier
        handler_id: str,
        phase: EnumHandlerExecutionPhase,
        capability_id: str
        | None = None,  # string-id-ok: user-facing capability identifier
    ) -> None:
        """
        Record hook execution start.

        Args:
            hook_id: Unique identifier for this hook execution
            handler_id: The handler that is executing
            phase: Execution phase
            capability_id: Associated capability if applicable
        """
        trace = ModelHookTrace(
            hook_id=hook_id,
            handler_id=handler_id,
            phase=phase,
            capability_id=capability_id,
            status=EnumExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._pending_hooks[hook_id] = trace

    @standard_error_handling("Hook execution completion")
    def complete_hook(
        self,
        hook_id: str,  # string-id-ok: user-facing hook identifier
        status: EnumExecutionStatus,
        error_message: str | None = None,
        error_code: str | None = None,
        skip_reason: str | None = None,
        output_hash: str | None = None,
        retry_count: int = 0,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """
        Record hook execution completion.

        Args:
            hook_id: The hook ID to complete
            status: Final execution status
            error_message: Error message if failed
            error_code: Error code if failed
            skip_reason: Reason if skipped
            output_hash: Hash of output data
            retry_count: Number of retries attempted
            metadata: Additional metadata
        """
        if hook_id not in self._pending_hooks:
            # Hook wasn't started - this is unexpected, log a warning
            warnings.warn(
                f"Completing hook '{hook_id}' that was never started. "
                "This may indicate a programming error or out-of-order hook completion.",
                stacklevel=2,
            )
            # Create a minimal trace to record the completion
            ended_at = datetime.now(UTC)
            trace = ModelHookTrace(
                hook_id=hook_id,
                handler_id="unknown",
                phase=EnumHandlerExecutionPhase.EXECUTE,
                status=status,
                started_at=ended_at,
                ended_at=ended_at,
                duration_ms=0.0,
                error_message=error_message,
                error_code=error_code,
                skip_reason=skip_reason,
            )
            self._hook_traces.append(trace)
            return

        # Get the pending trace
        pending = self._pending_hooks.pop(hook_id)
        ended_at = datetime.now(UTC)
        duration_ms = (ended_at - pending.started_at).total_seconds() * 1000

        # Create completed trace (frozen model requires recreation)
        completed = ModelHookTrace(
            hook_id=pending.hook_id,
            handler_id=pending.handler_id,
            phase=pending.phase,
            capability_id=pending.capability_id,
            status=status,
            started_at=pending.started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            error_message=error_message,
            error_code=error_code,
            skip_reason=skip_reason,
            output_hash=output_hash,
            retry_count=retry_count,
            input_hash=pending.input_hash,
            metadata=metadata,
        )
        self._hook_traces.append(completed)

    # === Emission Recording ===

    @standard_error_handling("Emission recording")
    def record_emission(
        self,
        emission_type: Literal["event", "intent", "projection", "action"],
        type_name: str,
    ) -> None:
        """
        Record an emitted output.

        Args:
            emission_type: Type of emission (event, intent, projection, action)
            type_name: Name of the specific type emitted
        """
        match emission_type:
            case "event":
                self._events.append(type_name)
            case "intent":
                self._intents.append(type_name)
            case "projection":
                self._projections.append(type_name)
            case "action":
                self._actions.append(type_name)

    def record_event(self, event_type: str) -> None:
        """Record an event emission."""
        self.record_emission("event", event_type)

    def record_intent(self, intent_type: str) -> None:
        """Record an intent emission."""
        self.record_emission("intent", intent_type)

    def record_projection(self, projection_type: str) -> None:
        """Record a projection update."""
        self.record_emission("projection", projection_type)

    def record_action(self, action_type: str) -> None:
        """Record an action emission."""
        self.record_emission("action", action_type)

    # === Failure Recording ===

    @standard_error_handling("Failure recording")
    def record_failure(
        self,
        error_code: str,
        error_message: str,
        phase: EnumHandlerExecutionPhase | None = None,
        handler_id: str | None = None,
        stack_trace: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """
        Record an execution failure.

        Args:
            error_code: Error code identifying the failure type
            error_message: Human-readable error message
            phase: Execution phase where failure occurred
            handler_id: Handler that failed
            stack_trace: Optional stack trace for debugging
            recoverable: Whether the failure is potentially recoverable
        """
        failure = ModelManifestFailure(
            failed_at=datetime.now(UTC),
            phase=phase,
            handler_id=handler_id,
            error_code=error_code,
            error_message=error_message,
            stack_trace=stack_trace,
            recoverable=recoverable,
        )
        self._failures.append(failure)

    # === Metrics Recording ===

    @standard_error_handling("Phase duration recording")
    def record_phase_duration(self, phase: str, duration_ms: float) -> None:
        """
        Record duration for a phase.

        Args:
            phase: Phase name
            duration_ms: Duration in milliseconds
        """
        self._phase_durations[phase] = duration_ms

    # === Size Estimation ===

    def estimate_json_size_bytes(self) -> int:
        """
        Estimate the JSON-serialized size of the manifest in bytes.

        This method provides a quick approximation of the manifest size without
        actually building and serializing it. Useful for:

        - Detecting large manifests before serialization (e.g., >1MB warning)
        - Making decisions about storage strategy (streaming vs. batch)
        - Monitoring manifest growth during long-running pipelines

        The estimate uses average byte sizes for different data types:

        - UUID: ~36 bytes (string representation)
        - datetime: ~24 bytes (ISO format)
        - Hook trace: ~500 bytes (includes all fields)
        - Capability activation: ~200 bytes
        - Dependency edge: ~150 bytes
        - Emission type: ~50 bytes

        Returns:
            Estimated size in bytes. Actual size may vary ±20% due to
            field value lengths and JSON formatting choices.

        Example:
            >>> generator = ManifestGenerator(...)
            >>> # ... record observations ...
            >>> size = generator.estimate_json_size_bytes()
            >>> if size > 1_000_000:  # 1MB
            ...     logger.warning(f"Large manifest detected: ~{size/1024:.0f}KB")

        .. versionadded:: 0.4.0
        """
        # Base overhead: manifest structure, IDs, timestamps
        base_size = 500  # UUIDs, timestamps, wrapper structure

        # Node and contract identity
        identity_size = 300  # Approximate size for identity models

        # Hook traces (largest contributor for long pipelines)
        hook_trace_size = 500  # Average bytes per trace
        traces_size = len(self._hook_traces) * hook_trace_size
        pending_size = len(self._pending_hooks) * hook_trace_size

        # Capability activations
        activation_size = 200  # Average bytes per activation
        activations_size = (
            len(self._activated_capabilities) + len(self._skipped_capabilities)
        ) * activation_size

        # Dependency edges
        edge_size = 150  # Average bytes per edge
        edges_size = len(self._dependency_edges) * edge_size

        # Emissions (type names as strings)
        emission_size = 50  # Average bytes per emission type
        emissions_count = (
            len(self._events)
            + len(self._intents)
            + len(self._projections)
            + len(self._actions)
        )
        emissions_size = emissions_count * emission_size

        # Failures
        failure_size = 400  # Average bytes per failure (includes stack trace estimate)
        failures_size = len(self._failures) * failure_size

        # Phase durations and resolved order
        metadata_size = len(self._phase_durations) * 50 + len(self._resolved_order) * 50

        return (
            base_size
            + identity_size
            + traces_size
            + pending_size
            + activations_size
            + edges_size
            + emissions_size
            + failures_size
            + metadata_size
        )

    # === Build Method ===

    def build(self) -> ModelExecutionManifest:
        """
        Build the final immutable manifest.

        Returns:
            The completed execution manifest

        Note:
            This method is intended to be called once at the end of pipeline
            execution. While calling multiple times is technically safe (pending
            hooks are removed on completion), each call creates a new manifest
            with the current accumulated state and auto-completes any remaining
            pending hooks as CANCELLED.
        """
        ended_at = datetime.now(UTC)
        total_duration_ms = (ended_at - self._started_at).total_seconds() * 1000

        # Complete any pending hooks as cancelled
        for hook_id, pending in list(self._pending_hooks.items()):
            self.complete_hook(
                hook_id,
                EnumExecutionStatus.CANCELLED,
                error_message="Hook not completed before manifest build",
            )

        # Build sub-models
        activation_summary = ModelActivationSummary(
            activated_capabilities=self._activated_capabilities,
            skipped_capabilities=self._skipped_capabilities,
            total_evaluated=len(self._activated_capabilities)
            + len(self._skipped_capabilities),
        )

        ordering_summary = ModelOrderingSummary(
            phases=self._phases,
            resolved_order=self._resolved_order,
            dependency_edges=self._dependency_edges,
            ordering_policy=self._ordering_policy,
            ordering_rationale=self._ordering_rationale,
        )

        emissions_summary = ModelEmissionsSummary(
            events_count=len(self._events),
            event_types=list(dict.fromkeys(self._events)),  # Unique, order-preserving
            intents_count=len(self._intents),
            intent_types=list(dict.fromkeys(self._intents)),
            projections_count=len(self._projections),
            projection_types=list(dict.fromkeys(self._projections)),
            actions_count=len(self._actions),
            action_types=list(dict.fromkeys(self._actions)),
        )

        # Build handler durations from traces
        # Note: Handlers may have multiple hook traces (e.g., different phases like
        # PREPARE, EXECUTE, CLEANUP). We sum all durations for the same handler_id
        # to get total time spent in that handler across all its hooks.
        handler_durations: dict[str, float] = {}
        for trace in self._hook_traces:
            if trace.handler_id in handler_durations:
                handler_durations[trace.handler_id] += trace.duration_ms
            else:
                handler_durations[trace.handler_id] = trace.duration_ms

        metrics_summary = ModelMetricsSummary(
            total_duration_ms=total_duration_ms,
            phase_durations_ms=self._phase_durations,
            handler_durations_ms=handler_durations,
        )

        manifest = ModelExecutionManifest(
            manifest_id=self._manifest_id,
            created_at=self._started_at,
            node_identity=self._node_identity,
            contract_identity=self._contract_identity,
            activation_summary=activation_summary,
            ordering_summary=ordering_summary,
            hook_traces=self._hook_traces,
            emissions_summary=emissions_summary,
            metrics_summary=metrics_summary,
            failures=self._failures,
            correlation_id=self._correlation_id,
            parent_manifest_id=self._parent_manifest_id,
        )

        # Invoke on_manifest_built callbacks (OMN-1203: corpus capture hook)
        # Snapshot the list to prevent modification during iteration
        for callback in list(self._on_manifest_built):
            try:
                callback(manifest)
            except Exception as e:
                # callback-resilience-ok: callbacks must not crash manifest build
                warnings.warn(
                    f"on_manifest_built callback failed: {e!r}. "
                    "Manifest was built successfully but callback raised an exception.",
                    stacklevel=2,
                )

        return manifest


# Export for use
__all__ = ["ManifestGenerator"]
