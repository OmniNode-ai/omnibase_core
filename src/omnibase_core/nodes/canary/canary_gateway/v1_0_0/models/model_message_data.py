"""Message data model for Gateway operations."""

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ModelMessageData(BaseModel):
    """Message data structure for gateway routing and aggregation."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    content: Dict[str, str]
    sender_id: str
    recipient_id: Optional[str] = None
    message_type: str = "default"
    priority: int = Field(default=1, ge=1, le=10)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True