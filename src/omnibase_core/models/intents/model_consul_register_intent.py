"""
Intent to register a service with Consul.

This module provides the ModelConsulRegisterIntent class for declaring
service registration with Consul service discovery.

Thread Safety:
    ModelConsulRegisterIntent is immutable (frozen=True) after creation.

Example:
    >>> from omnibase_core.models.intents import ModelConsulRegisterIntent
    >>> from uuid import uuid4
    >>> intent = ModelConsulRegisterIntent(
    ...     service_id="node-123",
    ...     service_name="onex-compute",
    ...     tags=["node_type:compute"],
    ...     correlation_id=uuid4(),
    ... )

See Also:
    - model_core_intent_base: Base class for core intents
    - model_consul_deregister_intent: Deregistration intent
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(
    "Consul service IDs are strings by design (external system constraint). "
    "Consul uses string identifiers for service instances, not UUIDs."
)
@allow_dict_str_any(
    "Health check configuration is passed directly to Consul API which accepts "
    "arbitrary string key-value pairs for check configuration."
)
class ModelConsulRegisterIntent(ModelCoreIntent):
    """Intent to register a service with Consul.

    Emitted by Reducers when a new service instance should be registered
    with Consul for service discovery. The Effect node executes this intent
    by calling the Consul registration API.

    Attributes:
        kind: Discriminator for intent routing ("consul.register").
        service_id: Unique service instance identifier (Consul format).
        service_name: Service name for discovery.
        tags: Service tags for filtering and metadata.
        health_check: Optional health check configuration.
    """

    kind: Literal["consul.register"] = Field(
        default="consul.register",
        description="Discriminator for intent routing",
    )
    service_id: str = Field(
        ...,
        description="Unique service instance identifier (Consul format)",
        min_length=1,
        max_length=200,
    )
    service_name: str = Field(
        ...,
        description="Service name for discovery",
        min_length=1,
        max_length=100,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Service tags for filtering and metadata",
    )
    health_check: dict[str, str] | None = Field(
        default=None,
        description="Optional health check configuration for Consul",
    )
