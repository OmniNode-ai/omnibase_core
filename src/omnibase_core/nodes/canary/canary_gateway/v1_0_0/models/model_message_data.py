"""Model for message data payload."""

from pydantic import BaseModel, Field


class ModelMessageData(BaseModel):
    """Model for message data payload."""

    content: str = Field(..., description="Message content")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Message metadata",
    )
    priority: int = Field(default=5, description="Message priority (1-10)")
    timestamp: str | None = Field(None, description="Message timestamp")
