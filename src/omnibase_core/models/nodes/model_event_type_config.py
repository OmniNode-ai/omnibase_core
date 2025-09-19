"""
Event type configuration model for publish/subscribe patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventTypeConfig(BaseModel):
    """Event type configuration for publish/subscribe patterns."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(
        ...,
        description="Event type name",
    )
    event_schema: str | None = Field(
        None,
        description="Event schema specification",
    )
    routing_key: str | None = Field(
        None,
        description="Routing key for the event",
    )
    persistence: bool = Field(
        default=False,
        description="Whether events should be persisted",
    )
