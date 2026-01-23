"""
Handler Behavior Model.

Defines runtime behavior characteristics for handlers embedded in contracts.
Part of the three-layer architecture: Profile -> Behavior -> Contract.

This model configures how handlers behave at runtime including purity,
idempotency, concurrency, isolation, and observability settings.

Note:
    This model was renamed from ModelHandlerDescriptor to ModelHandlerBehavior
    to avoid collision with the registry-focused ModelHandlerDescriptor in
    omnibase_core.models.handlers.model_handler_descriptor.

Related:
    - OMN-1125: Default Profile Factory for Contracts
    - OMN-1465: Rename handler_kind to node_archetype
    - ModelExecutionProfile: Profile layer (execution resource allocation)
    - ModelContractBase: Contract layer (declarative node specification)

.. versionadded:: 0.4.0
.. versionchanged:: 0.9.2
    Renamed ``handler_kind`` to ``node_archetype`` with ``EnumNodeArchetype`` type.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from omnibase_core.enums.enum_node_archetype import EnumNodeArchetype
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)


def _coerce_node_archetype(v: object) -> EnumNodeArchetype | object:
    """Coerce string values to EnumNodeArchetype for YAML/JSON parsing."""
    if isinstance(v, str):
        try:
            return EnumNodeArchetype(v)
        except ValueError:
            return v  # Let Pydantic handle the validation error
    return v


# Type alias for node_archetype field with automatic string coercion.
# Use this type in any model that accepts node archetype from external sources (YAML, JSON).
NodeArchetypeField = Annotated[
    EnumNodeArchetype, BeforeValidator(_coerce_node_archetype)
]

__all__ = [
    "ModelHandlerBehavior",
    "NodeArchetypeField",
]


class ModelHandlerBehavior(BaseModel):
    """Handler behavior configuration embedded in contracts.

    Defines runtime behavior characteristics for handlers including purity,
    idempotency, concurrency, isolation, and observability. This model is
    part of the three-layer architecture:

    1. **Profile** (ModelExecutionProfile): Resource allocation and execution
       environment settings (CPU, memory, timeout defaults).
    2. **Behavior** (this model): Handler behavior configuration embedded
       in contracts defining how the handler operates.
    3. **Contract** (ModelContractBase): Full declarative node specification
       including I/O schemas, dependencies, and metadata.

    Node Archetype Semantics:
        - **compute**: Pure data transformation, no side effects, cacheable
        - **effect**: External I/O operations, side-effecting, requires isolation
        - **reducer**: State aggregation, FSM-driven, intent-based transitions
        - **orchestrator**: Workflow coordination, emits events/intents only

    Purity and Idempotency:
        - **pure**: Function has no side effects, same input = same output
        - **side_effecting**: Function may modify external state
        - **idempotent**: Multiple identical calls produce same result

    Concurrency Policies:
        - **parallel_ok**: Handler can run concurrently with itself
        - **serialized**: Handler executes one at a time (default)
        - **singleflight**: Deduplicate concurrent calls with same input

    Isolation Policies:
        - **none**: No isolation, runs in same process (default)
        - **process**: Runs in separate process
        - **container**: Runs in isolated container
        - **vm**: Runs in isolated virtual machine

    Observability Levels:
        - **minimal**: Basic metrics only (latency, success/failure)
        - **standard**: Metrics plus structured logging (default)
        - **verbose**: Full tracing, detailed logs, performance profiling

    Attributes:
        node_archetype: Architectural role of the handler (compute/effect/etc).
        purity: Whether handler is pure or side-effecting.
        idempotent: Whether handler is idempotent (safe to retry).
        timeout_ms: Handler timeout in milliseconds (None = use profile default).
        retry_policy: Retry configuration for transient failures.
        circuit_breaker: Circuit breaker configuration for fault tolerance.
        concurrency_policy: How concurrent handler invocations are managed.
        isolation_policy: Process/container isolation level for handler.
        observability_level: Telemetry verbosity for the handler.
        capability_inputs: Required input capabilities (e.g., ["http", "json"]).
        capability_outputs: Provided output capabilities (e.g., ["event", "log"]).

    Example:
        >>> behavior = ModelHandlerBehavior(
        ...     node_archetype="compute",
        ...     purity="pure",
        ...     idempotent=True,
        ...     timeout_ms=5000,
        ...     concurrency_policy="parallel_ok",
        ...     observability_level="standard",
        ... )

        >>> # Effect handler with retry and circuit breaker
        >>> effect_behavior = ModelHandlerBehavior(
        ...     node_archetype="effect",
        ...     purity="side_effecting",
        ...     idempotent=True,  # Required for retry
        ...     timeout_ms=30000,
        ...     retry_policy=ModelDescriptorRetryPolicy(
        ...         enabled=True,
        ...         max_retries=3,
        ...     ),
        ...     circuit_breaker=ModelDescriptorCircuitBreaker(
        ...         enabled=True,
        ...         failure_threshold=5,
        ...     ),
        ... )

    See Also:
        - EnumNodeArchetype: Enum defining node archetype values
        - ModelExecutionProfile: Profile layer for resource allocation
        - ModelContractBase: Contract layer for full node specification
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_archetype: NodeArchetypeField = Field(
        ...,
        description="Architectural role of the handler in the ONEX workflow",
    )

    purity: Literal["pure", "side_effecting"] = Field(
        default="side_effecting",
        description="Whether handler is pure (no side effects) or side-effecting",
    )

    idempotent: bool = Field(
        default=False,
        description="Whether handler is idempotent (safe to retry with same input)",
    )

    timeout_ms: int | None = Field(
        default=None,
        ge=0,
        description="Handler timeout in milliseconds (None = use profile default)",
    )

    retry_policy: ModelDescriptorRetryPolicy | None = Field(
        default=None,
        description="Retry configuration for handling transient failures",
    )

    circuit_breaker: ModelDescriptorCircuitBreaker | None = Field(
        default=None,
        description="Circuit breaker configuration for fault tolerance",
    )

    concurrency_policy: Literal["parallel_ok", "serialized", "singleflight"] = Field(
        default="serialized",
        description="How concurrent handler invocations are managed",
    )

    isolation_policy: Literal["none", "process", "container", "vm"] = Field(
        default="none",
        description="Process/container isolation level for handler execution",
    )

    observability_level: Literal["minimal", "standard", "verbose"] = Field(
        default="standard",
        description="Telemetry and logging verbosity for the handler",
    )

    capability_inputs: list[str] = Field(
        default_factory=list,
        description="Required input capabilities (e.g., ['http', 'json'])",
    )

    capability_outputs: list[str] = Field(
        default_factory=list,
        description="Provided output capabilities (e.g., ['event', 'log'])",
    )
