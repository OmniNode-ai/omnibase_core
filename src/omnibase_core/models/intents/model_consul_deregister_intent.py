"""
Intent to deregister a service from Consul.

This module provides the ModelConsulDeregisterIntent class for declaring
service deregistration from Consul service discovery.

Thread Safety:
    ModelConsulDeregisterIntent is immutable (frozen=True) after creation.

Example:
    >>> from omnibase_core.models.intents import ModelConsulDeregisterIntent
    >>> from uuid import uuid4
    >>> intent = ModelConsulDeregisterIntent(
    ...     service_id="node-123",
    ...     correlation_id=uuid4(),
    ... )

See Also:
    - model_core_intent_base: Base class for core intents
    - model_consul_register_intent: Registration intent
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
    """Intent to deregister a service from Consul.

    Emitted by Reducers when a service instance should be removed from
    Consul service discovery. The Effect node executes this intent by
    calling the Consul deregistration API.

    Attributes:
        kind: Discriminator for intent routing ("consul.deregister").
        service_id: Service instance identifier to deregister.
    """

    kind: Literal["consul.deregister"] = Field(
        default="consul.deregister",
        description="Discriminator for intent routing",
    )
    service_id: str = Field(
        ...,
        description="Service instance identifier to deregister (Consul format)",
        min_length=1,
        max_length=200,
    )
