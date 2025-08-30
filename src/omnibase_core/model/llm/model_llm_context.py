"""
LLM context model for request context data.

Provides strongly-typed context structure to replace Dict[str, Any] usage.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmContext(BaseModel):
    """
    Context entry for LLM requests.

    Replaces Dict[str, Any] usage in context fields.
    """

    context_type: str = Field(
        description="Type of context: system, user, assistant, function"
    )

    content: str = Field(description="Context content or message")

    role: Optional[str] = Field(
        default=None, description="Role in conversation context"
    )

    timestamp: Optional[str] = Field(
        default=None, description="When this context was created (ISO format)"
    )

    source: Optional[str] = Field(
        default=None, description="Source of this context entry"
    )

    importance: Optional[float] = Field(
        default=None, description="Importance weight for this context (0-1)"
    )

    context_id: Optional[str] = Field(
        default=None, description="Unique identifier for this context entry"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
