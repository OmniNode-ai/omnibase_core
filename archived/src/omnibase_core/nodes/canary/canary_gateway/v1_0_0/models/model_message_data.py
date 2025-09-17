"""Message data model for Gateway operations."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelMessageData(BaseModel):
    """Message data structure for gateway routing and aggregation."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    content: dict[str, str]
    sender_id: str
    recipient_id: str | None = None
    message_type: str = "default"
    priority: int = Field(default=1, ge=1, le=10)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, str] | None = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
