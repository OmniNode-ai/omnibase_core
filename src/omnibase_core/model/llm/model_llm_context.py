"""
LLM context model for request context data.

Provides strongly-typed context structure to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmContext(BaseModel):
    """
    Context entry for LLM requests.

    Replaces Dict[str, Any] usage in context fields.
    """

    context_type: str = Field(
        description="Type of context: system, user, assistant, function",
    )

    content: str = Field(description="Context content or message")

    role: str | None = Field(
        default=None,
        description="Role in conversation context",
    )

    timestamp: str | None = Field(
        default=None,
        description="When this context was created (ISO format)",
    )

    source: str | None = Field(
        default=None,
        description="Source of this context entry",
    )

    importance: float | None = Field(
        default=None,
        description="Importance weight for this context (0-1)",
    )

    context_id: str | None = Field(
        default=None,
        description="Unique identifier for this context entry",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
