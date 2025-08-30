"""Strongly typed model for conversation interaction entries."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.model.conversation.model_conversation_metadata import \
    ModelConversationMetadata


class ModelConversationInteractionEntry(BaseModel):
    """Strongly typed model for conversation interaction entries during capture."""

    interaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique interaction identifier",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Interaction timestamp"
    )
    user_message: str = Field(..., description="User message (truncated)")
    assistant_action: str = Field(
        ..., description="Assistant action/response (truncated)"
    )
    tools_used: List[str] = Field(
        default_factory=list, description="Tools used in this interaction"
    )
    outcome: str = Field(default="in_progress", description="Interaction outcome")
    metadata: Optional[ModelConversationMetadata] = Field(
        None, description="Additional metadata"
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
