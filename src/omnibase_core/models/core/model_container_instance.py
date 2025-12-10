#!/usr/bin/env python3
"""
Container Instance Model.

Strongly-typed model for ONEX container instances used in service resolution.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.container.model_service_registration import (
    ModelServiceRegistration,
)
from omnibase_core.models.core.model_protocol_registration import (
    ModelProtocolRegistration,
)


class ModelContainerInstance(BaseModel):
    """Container instance model for service resolution."""

    container_id: UUID = Field(description="Unique identifier for container instance")
    service_registrations: list[ModelServiceRegistration] = Field(
        default_factory=list,
        description="Registered services",
    )
    protocol_registrations: list[ModelProtocolRegistration] = Field(
        default_factory=list,
        description="Registered protocol implementations",
    )
