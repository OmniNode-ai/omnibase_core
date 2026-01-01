"""
Intent to register a service with Consul.

This module provides the ModelConsulRegisterIntent class for declaring
service registration with Consul service discovery. This is a core intent
that participates in the discriminated union pattern for type-safe handling.

Design Pattern:
    Reducers emit this intent when a service instance should become discoverable.
    The Effect node receives the intent via ModelCoreRegistrationIntent union,
    pattern-matches on the `kind` discriminator, and executes the Consul API call.

    This separation ensures Reducer purity - the Reducer declares the desired
    outcome without performing the actual side effect.

Consul Integration:
    - service_id: Must be unique within the Consul datacenter
    - service_name: Logical service name for discovery queries
    - tags: Used for service filtering (e.g., "env:production", "version:1.2.3")
    - health_check: Optional Consul health check configuration

Thread Safety:
    ModelConsulRegisterIntent is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.intents import ModelConsulRegisterIntent
    >>> from uuid import uuid4
    >>>
    >>> # Basic registration
    >>> intent = ModelConsulRegisterIntent(
    ...     service_id="node-compute-abc123",
    ...     service_name="onex-compute",
    ...     tags=["node_type:compute", "env:production"],
    ...     correlation_id=uuid4(),
    ... )
    >>>
    >>> # With health check
    >>> intent_with_health = ModelConsulRegisterIntent(
    ...     service_id="node-api-def456",
    ...     service_name="onex-api",
    ...     tags=["node_type:effect"],
    ...     health_check={"HTTP": "http://localhost:8080/health", "Interval": "10s"},
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents.ModelCoreIntent: Base class for core intents
    omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union type
    omnibase_core.models.intents.ModelConsulDeregisterIntent: Deregistration intent
"""

from typing import Any, Literal

from pydantic import Field

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    "Consul service IDs are strings by design (external system constraint). "
    "Consul uses string identifiers for service instances, not UUIDs."
)
class ModelConsulRegisterIntent(ModelCoreIntent):
    """Intent to register a service with Consul service discovery.

    Emitted by Reducers when a new service instance should be registered
    with Consul for service discovery. The Effect node executes this intent
    by calling the Consul registration API.

    This intent participates in the ModelCoreRegistrationIntent discriminated
    union, enabling exhaustive pattern matching in Effect nodes.

    Effect Pattern - Intent to Execution Flow:
        This intent is part of the ONEX Reducer -> Effect architecture:

        1. **Reducer emits intent** (pure, no side effects):
           ```python
           def reduce(state: NodeState, action: StartupAction) -> tuple[NodeState, list[Intent]]:
               return (
                   state.with_status("registering"),
                   [ModelConsulRegisterIntent(
                       kind="consul.register",
                       service_id=f"node-{state.node_id}",
                       service_name="onex-compute",
                       tags=["node_type:compute"],
                       correlation_id=action.correlation_id,
                   )]
               )
           ```

        2. **Effect receives and executes** (performs side effect):
           ```python
           class NodeConsulEffect(NodeEffect):
               async def execute(self, intent: ModelCoreRegistrationIntent) -> None:
                   match intent:
                       case ModelConsulRegisterIntent():
                           await self.consul_client.register(
                               service_id=intent.service_id,
                               service_name=intent.service_name,
                               tags=intent.tags,
                               check=intent.health_check,
                           )
           ```

        3. **Correlation ID enables tracing** across the entire flow.

    Attributes:
        kind: Discriminator literal for intent routing. Always "consul.register".
            Used by Pydantic's discriminated union to route to correct handler.
            Placed first for optimal union type resolution performance.
        service_id: Unique service instance identifier in Consul format. Must be
            unique within the Consul datacenter. Typically includes node type
            and a unique suffix (e.g., "node-compute-abc123").
        service_name: Logical service name for discovery queries. Multiple service
            instances can share the same service_name for load balancing.
        tags: Service tags for filtering and metadata. Common patterns include
            "node_type:compute", "env:production", "version:1.2.3".
        health_check: Optional Consul health check configuration. Passed directly
            to Consul API. Common keys: "HTTP", "Interval", "Timeout", "TCP".

    Example:
        >>> from omnibase_core.models.intents import ModelConsulRegisterIntent
        >>> from uuid import uuid4
        >>>
        >>> intent = ModelConsulRegisterIntent(
        ...     kind="consul.register",
        ...     service_id="node-compute-abc123",
        ...     service_name="onex-compute",
        ...     tags=["node_type:compute"],
        ...     correlation_id=uuid4(),
        ... )

    See Also:
        omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union
        omnibase_core.models.intents.ModelConsulDeregisterIntent: Deregistration intent
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    # Pydantic checks fields in order when resolving discriminated unions,
    # so having the discriminator first speeds up type matching.
    kind: Literal["consul.register"] = Field(
        default="consul.register",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )
    service_id: str = Field(
        ...,
        description=(
            "Unique service instance identifier in Consul format. Must be unique "
            "within the Consul datacenter. Example: 'node-compute-abc123'."
        ),
        min_length=1,
        max_length=200,
    )
    service_name: str = Field(
        ...,
        description=(
            "Logical service name for discovery queries. Multiple instances can "
            "share the same name for load balancing. Example: 'onex-compute'."
        ),
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )
    tags: list[str] = Field(
        default_factory=list,
        description=(
            "Service tags for filtering and metadata. Common patterns: "
            "'node_type:compute', 'env:production', 'version:1.2.3'."
        ),
    )
    # ONEX_EXCLUDE: dict_str_any - consul api health check configuration format
    health_check: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional Consul health check configuration. Passed directly to Consul "
            "API. Common keys: 'HTTP', 'Interval', 'Timeout', 'TCP'."
        ),
    )
