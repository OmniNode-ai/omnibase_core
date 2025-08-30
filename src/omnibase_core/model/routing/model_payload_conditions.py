"""ModelPayloadConditions: Strongly typed routing payload conditions"""

from pydantic import BaseModel, Field


class ModelPayloadConditions(BaseModel):
    """Strongly typed routing payload conditions"""

    event_type_pattern: str | None = Field(
        None,
        description="Event type pattern to match",
    )
    source_service_pattern: str | None = Field(
        None,
        description="Source service pattern to match",
    )
    payload_type_pattern: str | None = Field(
        None,
        description="Payload type pattern to match",
    )
    priority_level: str | None = Field(None, description="Priority level to match")
    minimum_payload_size: int | None = Field(
        None,
        description="Minimum payload size in bytes",
    )
    maximum_payload_size: int | None = Field(
        None,
        description="Maximum payload size in bytes",
    )
