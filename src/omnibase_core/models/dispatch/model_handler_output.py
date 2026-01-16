"""
Handler Output Model.

Unified handler output model per OMN-941 (Option A: Semantic Model).
This is the canonical return type for all message handlers in the ONEX dispatch engine.

Design Pattern:
    ModelHandlerOutput[T] implements Option A semantic constraints that enforce
    node-kind-specific output restrictions at the model level:

    - **ORCHESTRATOR**: Can emit events[] and intents[], but NOT projections[] or result
      (workflow coordination - dispatches work, doesn't maintain read state)

    - **REDUCER**: Can emit projections[] ONLY, no events[], intents[], or result
      (pure fold function - updates read-optimized state projections)

    - **EFFECT**: Can emit events[] ONLY, no intents[], projections[], or result
      (I/O boundary - publishes result events about external interactions)

    - **COMPUTE**: MUST return result, CANNOT emit events[], intents[], or projections[]
      (pure awaited transformation - returns typed result, no side effects)

    These constraints are enforced via Pydantic model validators and cannot
    be bypassed at runtime, ensuring architectural compliance.

COMPUTE Node Semantics:
    COMPUTE nodes are pure transformations (no side effects) that return an awaited result.
    They are referentially transparent at the business level: same input → same output.

    COMPUTE results must be "JSON-ledger-safe":
    - JSON primitives: str, int, float, bool, None
    - JSON containers: list, dict (with str keys and JSON-safe values)
    - Pydantic BaseModel (serializes to JSON)

    If a COMPUTE node needs to emit events, it is misclassified - use EFFECT instead.

Causality Tracking:
    Every ModelHandlerOutput MUST include:
    - input_envelope_id: The envelope_id of the input that triggered this handler
    - correlation_id: MUST be copied from the input envelope, not generated

    This enables full causality tracing in the dispatch engine.

Thread Safety:
    ModelHandlerOutput is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelHandlerOutput
    >>> from omnibase_core.enums import EnumNodeKind
    >>> from uuid import uuid4
    >>>
    >>> # Create output for an ORCHESTRATOR handler
    >>> output = ModelHandlerOutput.for_orchestrator(
    ...     input_envelope_id=uuid4(),
    ...     correlation_id=uuid4(),
    ...     handler_id="order-workflow-handler",
    ...     events=(some_event_envelope,),
    ...     intents=(create_order_intent,),
    ... )
    >>>
    >>> # Create output for a REDUCER handler
    >>> output = ModelHandlerOutput.for_reducer(
    ...     input_envelope_id=uuid4(),
    ...     correlation_id=uuid4(),
    ...     handler_id="user-state-reducer",
    ...     projections=(user_projection,),
    ... )
    >>>
    >>> # Create output for a COMPUTE handler
    >>> output = ModelHandlerOutput.for_compute(
    ...     input_envelope_id=uuid4(),
    ...     correlation_id=uuid4(),
    ...     handler_id="data-transform-compute",
    ...     result=transformed_data,  # Required for COMPUTE
    ... )

See Also:
    omnibase_core.models.dispatch.ModelDispatchResult: Dispatch operation result
    omnibase_core.models.dispatch.ModelHandlerRegistration: Handler metadata
    omnibase_core.enums.EnumNodeKind: Node type classification

Builder Method Default Metrics Behavior:
    All builder methods (for_orchestrator, for_reducer, for_effect, for_compute,
    for_void_compute) accept an optional `metrics` parameter of type `dict[str, float] | None`.

    **Default Behavior**:
    - When `metrics=None` (default): Converted to empty dict `{}` via `metrics or {}`
    - When `metrics={}` (explicit empty): Preserved as-is (already falsy, so `or {}` returns new `{}`)
    - When `metrics={...}` (non-empty): Used directly without modification

    **Why `metrics or {}` instead of `metrics if metrics is not None else {}`**:
    - Both patterns produce identical behavior for this use case
    - `metrics or {}` is more concise and Pythonic for optional dict parameters
    - Empty dict `{}` is falsy, so `{} or {}` returns a new `{}`
    - This ensures builders always pass a concrete dict to the model, never None

    **Example**:
        >>> # All three produce the same result:
        >>> output1 = ModelHandlerOutput.for_compute(..., metrics=None)       # → {}
        >>> output2 = ModelHandlerOutput.for_compute(..., metrics={})         # → {}
        >>> output3 = ModelHandlerOutput.for_compute(...)                      # → {}
        >>> assert output1.metrics == output2.metrics == output3.metrics == {}

        >>> # Non-empty metrics preserved:
        >>> output4 = ModelHandlerOutput.for_compute(..., metrics={"count": 5.0})
        >>> assert output4.metrics == {"count": 5.0}

    **Model Field Default**:
    The underlying Pydantic model field uses `default_factory=dict` (line 292),
    which means if you construct ModelHandlerOutput directly without `metrics`,
    it will also default to an empty dict. Builder methods ensure consistency
    by always passing an explicit dict value.

Future Enhancement:
    ModelComputeResult wrapper for complex payloads:
        - value: Any (restricted to ledger-safe types)
        - encoding: str (e.g., "json", "base64", "text")
        - type_name: str (runtime type hint)
        - schema_ref: str | None (optional JSON schema reference)
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type variable for COMPUTE result
T = TypeVar("T")


def _is_json_ledger_safe(value: Any) -> bool:
    """
    Check if a value is JSON-ledger-safe for COMPUTE results.

    JSON-ledger-safe values can be:
    - JSON primitives: str, int, float, bool, None
    - JSON containers: list, tuple, dict (with str keys and JSON-safe values)
    - Pydantic BaseModel (serializes to JSON via model_dump())

    NOT ledger-safe (rejected):
    - bytes, bytearray (use ModelComputeResult wrapper for binary)
    - datetime, UUID, Decimal (must be normalized to str first)
    - Custom classes without Pydantic serialization

    Args:
        value: The value to check

    Returns:
        True if value is JSON-ledger-safe, False otherwise

    Example:
        >>> _is_json_ledger_safe({"key": "value", "count": 42})
        True
        >>> _is_json_ledger_safe(datetime.now())
        False
    """
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, BaseModel):
        return True
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_json_ledger_safe(v) for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_is_json_ledger_safe(v) for v in value)
    # Reject everything else: bytes, datetime, UUID, Decimal, custom objects
    return False


class ModelHandlerOutput(BaseModel, Generic[T]):
    """
    Unified handler output model per OMN-941 (Option A Semantic Model).

    This is the canonical return type for all message handlers in the ONEX
    dispatch engine. It enforces node-kind-specific output constraints at
    the model level to ensure architectural compliance.

    Option A Constraints (Updated):
        - ORCHESTRATOR: events[], intents[] only (no projections[], no result)
        - REDUCER: projections[] only (no events[], no intents[], no result)
        - EFFECT: events[] only (no intents[], no projections[], no result)
        - COMPUTE: result only (no events[], no intents[], no projections[])

    Type Parameter:
        T: The type of the result for COMPUTE nodes. Must be JSON-ledger-safe:
           - JSON primitives (str, int, float, bool, None)
           - JSON containers (list, dict with str keys)
           - Pydantic BaseModel

    Attributes:
        input_envelope_id: ID of input envelope that triggered this handler.
            Required for causality tracking.
        correlation_id: MUST be copied from input envelope, not generated.
            Required for request tracing and correlation.
        dispatch_id: Dispatch operation ID that triggered this handler.
            Uniquely identifies the dispatch() call. None if created outside dispatch context.
        handler_id: Unique identifier from handler registry metadata.
        node_kind: The ONEX node kind from handler registry metadata.
        events: Tuple of event envelopes to publish (for ORCHESTRATOR, EFFECT only).
        intents: Tuple of intents for side-effect execution (for ORCHESTRATOR only).
        projections: Tuple of projection updates (for REDUCER only).
        result: Typed result value (for COMPUTE only). Must be JSON-ledger-safe.
        allow_void_compute: If True, COMPUTE may return None result (default: False).
        metrics: Dictionary of handler-specific metrics (e.g., processing counts).
        logs: Tuple of log entries generated during handler execution.
        processing_time_ms: Time taken to process the input in milliseconds.
        timestamp: When this output was created (UTC).

    Example:
        >>> from uuid import uuid4
        >>> output = ModelHandlerOutput(
        ...     input_envelope_id=uuid4(),
        ...     correlation_id=uuid4(),
        ...     handler_id="my-handler",
        ...     node_kind=EnumNodeKind.EFFECT,
        ...     events=(event_envelope,),
        ... )
        >>> output.has_outputs()
        True
        >>>
        >>> # COMPUTE with typed result
        >>> output = ModelHandlerOutput[MyResultModel](
        ...     input_envelope_id=uuid4(),
        ...     correlation_id=uuid4(),
        ...     handler_id="my-compute",
        ...     node_kind=EnumNodeKind.COMPUTE,
        ...     result=my_result,
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Causality Tracking (REQUIRED - from input envelope) ----
    input_envelope_id: UUID = Field(
        ...,
        description="ID of input envelope that triggered this handler. Required for causality tracking.",
    )
    correlation_id: UUID = Field(
        ...,
        description="MUST be copied from input envelope, not generated. Required for request tracing.",
    )
    dispatch_id: UUID | None = Field(
        default=None,
        description=(
            "Dispatch operation ID for request tracing. Uniquely identifies "
            "the dispatch() call that triggered this handler. All outputs from handlers "
            "invoked in the same dispatch share this ID. None for outputs created outside "
            "the dispatch engine context."
        ),
    )

    # ---- Handler Identity (derived from registry metadata) ----
    handler_id: str = Field(
        ...,
        description="Unique identifier from handler registry metadata.",
        min_length=1,
        max_length=200,
    )
    node_kind: EnumNodeKind = Field(
        ...,
        description="The ONEX node kind from handler registry metadata.",
    )

    # ---- Handler Outputs (Option A constraints enforced by validator) ----
    # Note: Using tuple[Any, ...] for collections to avoid circular imports at runtime.
    # Type hints are documented; runtime validation is the caller's responsibility.
    # Actual types:
    #   - events: tuple[ModelEventEnvelope[Any], ...]
    #   - intents: tuple[ModelIntent, ...]
    #   - projections: tuple[ModelProjectionBase, ...]
    events: tuple[Any, ...] = Field(
        default=(),
        description=(
            "Event envelopes to publish. Allowed for ORCHESTRATOR and EFFECT only. "
            "COMPUTE nodes must NOT emit events. "
            "Expected type: tuple[ModelEventEnvelope[Any], ...]"
        ),
    )
    intents: tuple[Any, ...] = Field(
        default=(),
        description=(
            "Intents for side-effect execution. Allowed for ORCHESTRATOR only. "
            "Expected type: tuple[ModelIntent, ...]"
        ),
    )
    projections: tuple[Any, ...] = Field(
        default=(),
        description=(
            "Projection updates. Allowed for REDUCER only. "
            "Expected type: tuple[ModelProjectionBase, ...]"
        ),
    )

    # ---- COMPUTE Result (Generic[T]) ----
    result: T | None = Field(
        default=None,
        description=(
            "Typed result value for COMPUTE nodes only. "
            "Must be JSON-ledger-safe: BaseModel, JSON primitives, or JSON containers. "
            "Required for COMPUTE unless allow_void_compute=True."
        ),
    )
    allow_void_compute: bool = Field(
        default=False,
        description=(
            "If True, COMPUTE may return None result (void computation). "
            "Default is False, meaning COMPUTE requires a non-None result."
        ),
    )

    # ---- Observability ----
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Handler-specific metrics (e.g., processing counts, custom timers).",
    )
    logs: tuple[str, ...] = Field(
        default=(),
        description="Log messages generated during handler execution.",
    )
    processing_time_ms: float = Field(
        default=0.0,
        description="Time taken to process the input in milliseconds.",
        ge=0.0,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this output was created (UTC).",
    )

    @model_validator(mode="after")
    def validate_node_kind_constraints(self) -> "ModelHandlerOutput[T]":
        """
        Enforce Option A node-kind output constraints.

        This validator ensures that handlers only emit outputs appropriate
        for their architectural role in the ONEX four-node architecture:

        - ORCHESTRATOR: Can emit events[] and intents[], but NOT projections[] or result
        - REDUCER: Can emit projections[] ONLY (pure fold - no events, no intents, no result)
        - EFFECT: Can emit events[] ONLY (I/O boundary - no intents, no projections, no result)
        - COMPUTE: MUST return result, CANNOT emit events[], intents[], or projections[]

        Additionally for COMPUTE:
        - result is required unless allow_void_compute=True
        - result must be JSON-ledger-safe (BaseModel, JSON primitives, or JSON containers)

        Raises:
            ModelOnexError: If the output contains fields not allowed for the node_kind

        Returns:
            Self if validation passes
        """
        if self.node_kind == EnumNodeKind.ORCHESTRATOR:
            if self.projections:
                raise ModelOnexError(
                    message=(
                        "ORCHESTRATOR cannot emit projections[] - use events[] and intents[] only. "
                        "Orchestrators coordinate workflows but do not maintain read-optimized state."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={
                        "node_kind": "ORCHESTRATOR",
                        "forbidden_field": "projections",
                    },
                )
            if self.result is not None:
                raise ModelOnexError(
                    message=(
                        "ORCHESTRATOR cannot set result - use events[] and intents[] only. "
                        "Only COMPUTE nodes return typed results."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "ORCHESTRATOR", "forbidden_field": "result"},
                )

        elif self.node_kind == EnumNodeKind.REDUCER:
            if self.events:
                raise ModelOnexError(
                    message=(
                        "REDUCER cannot emit events[] (pure fold - projections[] only). "
                        "Reducers maintain read-optimized state projections, not publish events."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "REDUCER", "forbidden_field": "events"},
                )
            if self.intents:
                raise ModelOnexError(
                    message=(
                        "REDUCER cannot emit intents[] (pure fold - projections[] only). "
                        "Reducers are pure functions that update state, not request side effects."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "REDUCER", "forbidden_field": "intents"},
                )
            if self.result is not None:
                raise ModelOnexError(
                    message=(
                        "REDUCER cannot set result (pure fold - projections[] only). "
                        "Only COMPUTE nodes return typed results."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "REDUCER", "forbidden_field": "result"},
                )

        elif self.node_kind == EnumNodeKind.EFFECT:
            if self.intents:
                raise ModelOnexError(
                    message=(
                        "EFFECT cannot emit intents[] - events[] only. "
                        "Effects execute side effects and publish result events, not request further effects."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "EFFECT", "forbidden_field": "intents"},
                )
            if self.projections:
                raise ModelOnexError(
                    message=(
                        "EFFECT cannot emit projections[] - events[] only. "
                        "Effects publish result events about external interactions, not update read state."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "EFFECT", "forbidden_field": "projections"},
                )
            if self.result is not None:
                raise ModelOnexError(
                    message=(
                        "EFFECT cannot set result - events[] only. "
                        "Only COMPUTE nodes return typed results."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "EFFECT", "forbidden_field": "result"},
                )

        elif self.node_kind == EnumNodeKind.COMPUTE:
            # COMPUTE must NOT emit anything - pure transformation returns result only
            if self.events:
                raise ModelOnexError(
                    message=(
                        "COMPUTE cannot emit events[] - result only. "
                        "COMPUTE nodes are pure transformations. If you need to emit events, use EFFECT."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "COMPUTE", "forbidden_field": "events"},
                )
            if self.intents:
                raise ModelOnexError(
                    message=(
                        "COMPUTE cannot emit intents[] - result only. "
                        "COMPUTE nodes are pure transformations, not side-effect requesters."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "COMPUTE", "forbidden_field": "intents"},
                )
            if self.projections:
                raise ModelOnexError(
                    message=(
                        "COMPUTE cannot emit projections[] - result only. "
                        "COMPUTE nodes transform data, not update read-optimized state."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "COMPUTE", "forbidden_field": "projections"},
                )

            # COMPUTE requires result (unless allow_void_compute)
            if self.result is None and not self.allow_void_compute:
                raise ModelOnexError(
                    message=(
                        "COMPUTE requires result (or set allow_void_compute=True for void computations). "
                        "COMPUTE nodes must return a typed result from their transformation."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                    context={"node_kind": "COMPUTE", "missing_field": "result"},
                )

            # COMPUTE result must be JSON-ledger-safe
            if self.result is not None and not _is_json_ledger_safe(self.result):
                raise ModelOnexError(
                    message=(
                        "COMPUTE result must be JSON-ledger-safe: BaseModel, JSON primitives "
                        "(str, int, float, bool, None), or JSON containers (list, dict with str keys). "
                        "For bytes or complex types, use a ModelComputeResult wrapper."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={
                        "node_kind": "COMPUTE",
                        "result_type": type(self.result).__name__,
                    },
                )

        # RUNTIME_HOST is infrastructure, not a message handler - no specific constraints
        # but typically wouldn't be used as a handler node_kind

        return self

    # ---- Convenience Methods ----

    def has_outputs(self) -> bool:
        """
        Check if this output contains any events, intents, projections, or result.

        Returns:
            True if any output is non-empty/non-None, False otherwise.

        Example:
            >>> output = ModelHandlerOutput(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="test",
            ...     node_kind=EnumNodeKind.EFFECT,
            ... )
            >>> output.has_outputs()
            False
        """
        return bool(
            self.events or self.intents or self.projections or self.result is not None
        )

    def output_count(self) -> int:
        """
        Get the total count of all outputs (events + intents + projections + result).

        For COMPUTE nodes, result counts as 1 if present.

        Returns:
            Total number of outputs across all collections plus result.

        Example:
            >>> output = ModelHandlerOutput.for_orchestrator(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="test",
            ...     events=(event1, event2),
            ...     intents=(intent1,),
            ... )
            >>> output.output_count()
            3
        """
        result_count = 1 if self.result is not None else 0
        return (
            len(self.events) + len(self.intents) + len(self.projections) + result_count
        )

    def has_result(self) -> bool:
        """
        Check if this output has a result (COMPUTE nodes only).

        Returns:
            True if result is not None, False otherwise.
        """
        return self.result is not None

    def has_metrics(self) -> bool:
        """
        Check if this output contains any metrics.

        Returns:
            True if metrics dictionary is non-empty, False otherwise.
        """
        return bool(self.metrics)

    def has_logs(self) -> bool:
        """
        Check if this output contains any log entries.

        Returns:
            True if logs tuple is non-empty, False otherwise.
        """
        return bool(self.logs)

    # ---- Builder Methods (Node-Kind Specific) ----

    @classmethod
    def for_orchestrator(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        events: tuple[Any, ...] = (),
        intents: tuple[Any, ...] = (),
        metrics: dict[str, float] | None = None,
        logs: tuple[str, ...] = (),
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[None]":
        """
        Create output for an ORCHESTRATOR handler.

        Orchestrators coordinate workflows and can emit events and intents,
        but NOT projections.

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            events: Event envelopes to publish (optional).
            intents: Intents for side-effect execution (optional).
            metrics: Handler-specific metrics (optional). Defaults to empty dict if None.
                    See module docstring "Builder Method Default Metrics Behavior" for details.
            logs: Log messages generated during execution (optional).
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput configured for ORCHESTRATOR.

        Example:
            >>> output = ModelHandlerOutput.for_orchestrator(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="order-workflow",
            ...     events=(order_created_event,),
            ...     intents=(send_email_intent,),
            ... )
        """
        return cast(
            ModelHandlerOutput[None],
            cls(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                dispatch_id=dispatch_id,
                handler_id=handler_id,
                node_kind=EnumNodeKind.ORCHESTRATOR,
                events=events,
                intents=intents,
                metrics=metrics or {},
                logs=logs,
                processing_time_ms=processing_time_ms,
            ),
        )

    @classmethod
    def for_reducer(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        projections: tuple[Any, ...] = (),
        metrics: dict[str, float] | None = None,
        logs: tuple[str, ...] = (),
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[None]":
        """
        Create output for a REDUCER handler.

        Reducers are pure fold functions that update read-optimized state
        projections. They can only emit projections, not events or intents.

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            projections: Projection updates (optional).
            metrics: Handler-specific metrics (optional). Defaults to empty dict if None.
                    See module docstring "Builder Method Default Metrics Behavior" for details.
            logs: Log messages generated during execution (optional).
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput configured for REDUCER.

        Example:
            >>> output = ModelHandlerOutput.for_reducer(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="user-state-reducer",
            ...     projections=(updated_user_projection,),
            ... )
        """
        return cast(
            ModelHandlerOutput[None],
            cls(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                dispatch_id=dispatch_id,
                handler_id=handler_id,
                node_kind=EnumNodeKind.REDUCER,
                projections=projections,
                metrics=metrics or {},
                logs=logs,
                processing_time_ms=processing_time_ms,
            ),
        )

    @classmethod
    def for_effect(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        events: tuple[Any, ...] = (),
        metrics: dict[str, float] | None = None,
        logs: tuple[str, ...] = (),
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[None]":
        """
        Create output for an EFFECT handler.

        Effects execute side effects (I/O operations) and publish facts
        about those interactions. They can only emit events, not intents
        or projections.

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            events: Event envelopes to publish (optional).
            metrics: Handler-specific metrics (optional). Defaults to empty dict if None.
                    See module docstring "Builder Method Default Metrics Behavior" for details.
            logs: Log messages generated during execution (optional).
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput configured for EFFECT.

        Example:
            >>> output = ModelHandlerOutput.for_effect(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="email-sender-effect",
            ...     events=(email_sent_event,),
            ... )
        """
        return cast(
            ModelHandlerOutput[None],
            cls(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                dispatch_id=dispatch_id,
                handler_id=handler_id,
                node_kind=EnumNodeKind.EFFECT,
                events=events,
                metrics=metrics or {},
                logs=logs,
                processing_time_ms=processing_time_ms,
            ),
        )

    @classmethod
    def for_compute(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        result: T | None = None,
        metrics: dict[str, float] | None = None,
        logs: tuple[str, ...] = (),
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[T]":
        """
        Create output for a COMPUTE handler.

        COMPUTE nodes are pure transformations that return a typed result.
        They CANNOT emit events, intents, or projections.

        The result must be JSON-ledger-safe:
        - JSON primitives (str, int, float, bool, None)
        - JSON containers (list, dict with str keys)
        - Pydantic BaseModel

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            result: The typed result of the computation (REQUIRED).
            metrics: Handler-specific metrics (optional). Defaults to empty dict if None.
                    See module docstring "Builder Method Default Metrics Behavior" for details.
            logs: Log messages generated during execution (optional).
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput[T] configured for COMPUTE with the result.

        Example:
            >>> output = ModelHandlerOutput.for_compute(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="data-transform-compute",
            ...     result={"transformed": True, "count": 42},
            ... )
        """
        return cls(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            dispatch_id=dispatch_id,
            handler_id=handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=result,
            metrics=metrics or {},
            logs=logs,
            processing_time_ms=processing_time_ms,
        )

    @classmethod
    def for_void_compute(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        metrics: dict[str, float] | None = None,
        logs: tuple[str, ...] = (),
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[None]":
        """
        Create output for a void COMPUTE handler (no result).

        Use this for COMPUTE nodes that perform side-effect-free transformations
        but don't need to return a value (e.g., validation-only computations).

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            metrics: Handler-specific metrics (optional). Defaults to empty dict if None.
                    See module docstring "Builder Method Default Metrics Behavior" for details.
            logs: Log messages generated during execution (optional).
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput[None] configured for void COMPUTE.

        Example:
            >>> output = ModelHandlerOutput.for_void_compute(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="validation-compute",
            ... )
        """
        return cast(
            ModelHandlerOutput[None],
            cls(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                dispatch_id=dispatch_id,
                handler_id=handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                allow_void_compute=True,
                metrics=metrics or {},
                logs=logs,
                processing_time_ms=processing_time_ms,
            ),
        )

    @classmethod
    def empty(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str = "",
        dispatch_id: UUID | None = None,
        node_kind: EnumNodeKind = EnumNodeKind.EFFECT,
        processing_time_ms: float = 0.0,
    ) -> "ModelHandlerOutput[None]":
        """
        Create an empty output with no events, intents, projections, or result.

        Useful when a handler processes a message but produces no outputs
        (e.g., filtering, logging, or idempotent duplicate detection).

        Note: For COMPUTE nodes, this automatically sets allow_void_compute=True.
        Consider using for_void_compute() explicitly for clarity.

        Args:
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.
            dispatch_id: Dispatch operation ID for request tracing (optional).
                None if created outside dispatch context.
            handler_id: Unique identifier for this handler.
            node_kind: The ONEX node kind for this handler.
            processing_time_ms: Processing time in milliseconds (optional).

        Returns:
            ModelHandlerOutput with no outputs.

        Example:
            >>> output = ModelHandlerOutput.empty(
            ...     input_envelope_id=uuid4(),
            ...     correlation_id=uuid4(),
            ...     handler_id="duplicate-filter",
            ...     node_kind=EnumNodeKind.EFFECT,
            ... )
            >>> output.has_outputs()
            False
        """
        # For COMPUTE nodes, allow void result
        allow_void = node_kind == EnumNodeKind.COMPUTE
        return cast(
            ModelHandlerOutput[None],
            cls(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                dispatch_id=dispatch_id,
                handler_id=handler_id,
                node_kind=node_kind,
                allow_void_compute=allow_void,
                processing_time_ms=processing_time_ms,
            ),
        )


__all__ = ["ModelHandlerOutput", "_is_json_ledger_safe"]
