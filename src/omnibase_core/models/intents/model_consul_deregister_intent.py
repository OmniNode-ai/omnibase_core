"""
Intent to deregister a service from Consul.

This module provides the ModelConsulDeregisterIntent class for declaring
service deregistration from Consul service discovery. This is a core intent
that participates in the discriminated union pattern for type-safe handling.

Design Pattern:
    Reducers emit this intent when a service instance should be removed from
    service discovery. The Effect node receives the intent via the
    ModelCoreRegistrationIntent union, pattern-matches on the `kind` discriminator,
    and executes the Consul deregistration API call.

    This separation ensures Reducer purity - the Reducer declares the desired
    outcome without performing the actual side effect.

Lifecycle Context:
    Typically emitted during:
    - Node shutdown (graceful termination)
    - Health check failures (self-removal)
    - Configuration changes (re-register with new settings)
    - Service migration (moving to different datacenter)

Thread Safety:
    ModelConsulDeregisterIntent is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.intents import ModelConsulDeregisterIntent
    >>> from uuid import uuid4
    >>>
    >>> # Graceful shutdown deregistration
    >>> intent = ModelConsulDeregisterIntent(
    ...     service_id="node-compute-abc123",
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents.ModelCoreIntent: Base class for core intents
    omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union type
    omnibase_core.models.intents.ModelConsulRegisterIntent: Registration intent
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    "Consul service IDs are strings by design (external system constraint). "
    "Consul uses string identifiers for service instances, not UUIDs."
)
class ModelConsulDeregisterIntent(ModelCoreIntent):
    """Intent to deregister a service from Consul service discovery.

    Emitted by Reducers when a service instance should be removed from
    Consul service discovery. The Effect node executes this intent by
    calling the Consul deregistration API.

    This intent participates in the ModelCoreRegistrationIntent discriminated
    union, enabling exhaustive pattern matching in Effect nodes.

    Effect Pattern - Intent to Execution Flow:
        This intent is part of the ONEX Reducer -> Effect architecture:

        1. **Reducer emits intent** (pure, no side effects):
           ```python
           def reduce(state: NodeState, action: ShutdownAction) -> tuple[NodeState, list[Intent]]:
               return (
                   state.with_status("deregistering"),
                   [ModelConsulDeregisterIntent(
                       kind="consul.deregister",
                       service_id=f"node-{state.node_id}",
                       correlation_id=action.correlation_id,
                   )]
               )
           ```

        2. **Effect receives and executes** (performs side effect):
           ```python
           class NodeConsulEffect(NodeEffect):
               async def execute(self, intent: ModelCoreRegistrationIntent) -> None:
                   match intent:
                       case ModelConsulDeregisterIntent():
                           await self.consul_client.deregister(
                               service_id=intent.service_id,
                           )
           ```

        3. **Correlation ID enables tracing** across the entire flow.

    Attributes:
        kind: Discriminator literal for intent routing. Always "consul.deregister".
            Used by Pydantic's discriminated union to route to correct handler.
            Placed first for optimal union type resolution performance.
        service_id: Service instance identifier to deregister in Consul format.
            Must match the service_id used during registration.

    Example:
        >>> from omnibase_core.models.intents import ModelConsulDeregisterIntent
        >>> from uuid import uuid4
        >>>
        >>> intent = ModelConsulDeregisterIntent(
        ...     kind="consul.deregister",
        ...     service_id="node-compute-abc123",
        ...     correlation_id=uuid4(),
        ... )

    See Also:
        omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union
        omnibase_core.models.intents.ModelConsulRegisterIntent: Registration intent
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    # Pydantic checks fields in order when resolving discriminated unions,
    # so having the discriminator first speeds up type matching.
    kind: Literal["consul.deregister"] = Field(
        default="consul.deregister",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )
    service_id: str = Field(
        ...,
        description=(
            "Service instance identifier to deregister in Consul format. Must match "
            "the service_id used during registration. Example: 'node-compute-abc123'."
        ),
        min_length=1,
        max_length=200,
    )
