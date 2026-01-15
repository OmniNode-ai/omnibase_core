"""
Event Definition Model.

Model for event definitions in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


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
        ...,  # REQUIRED - specify in contract
        description="Schema version for event structure (MUST be provided in YAML contract)",
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
