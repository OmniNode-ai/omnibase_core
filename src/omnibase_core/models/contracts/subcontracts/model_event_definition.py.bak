from typing import Any, Optional

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Event Definition Model - ONEX Standards Compliant.

Model for event definitions in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel


class ModelEventDefinition(BaseModel):
    """
    Event definition for event-driven architecture.

    Defines event types, structure, routing rules,
    and transformation logic for event processing.
    """

    event_name: str = Field(
        default=...,
        description="Unique name for the event type",
        min_length=1,
    )

    event_category: str = Field(
        default=...,
        description="Category classification for event routing",
        min_length=1,
    )

    description: str = Field(
        default=...,
        description="Human-readable event description",
        min_length=1,
    )

    schema_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Schema version for event structure",
    )

    required_fields: list[str] = Field(
        default_factory=list,
        description="Required fields in event payload",
    )

    optional_fields: list[str] = Field(
        default_factory=list,
        description="Optional fields in event payload",
    )

    routing_key: str | None = Field(
        default=None,
        description="Routing key for event distribution",
    )

    priority: int = Field(
        default=1,
        description="Event priority for processing order",
        ge=1,
        le=10,
    )

    ttl_seconds: int | None = Field(
        default=None,
        description="Time-to-live for event persistence",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
