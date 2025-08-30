"""ModelPayloadConditions: Strongly typed routing payload conditions"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelPayloadConditions(BaseModel):
    """Strongly typed routing payload conditions"""

    event_type_pattern: Optional[str] = Field(
        None, description="Event type pattern to match"
    )
    source_service_pattern: Optional[str] = Field(
        None, description="Source service pattern to match"
    )
    payload_type_pattern: Optional[str] = Field(
        None, description="Payload type pattern to match"
    )
    priority_level: Optional[str] = Field(None, description="Priority level to match")
    minimum_payload_size: Optional[int] = Field(
        None, description="Minimum payload size in bytes"
    )
    maximum_payload_size: Optional[int] = Field(
        None, description="Maximum payload size in bytes"
    )
