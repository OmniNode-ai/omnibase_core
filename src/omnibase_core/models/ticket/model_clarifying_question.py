"""Clarifying question model for ticket requirements."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelClarifyingQuestion(BaseModel):
    """A clarifying question for ticket requirements.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the question")
    text: str = Field(..., description="The question text")
    category: Literal["scope", "technical", "acceptance", "timeline", "dependency"] = (
        Field(..., description="Category of the question")
    )
    required: bool = Field(
        default=True, description="Whether an answer is required to proceed"
    )
    answer: str | None = Field(default=None, description="The answer to the question")
    answered_at: datetime | None = Field(
        default=None, description="When the question was answered"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


# Alias for cleaner imports
ClarifyingQuestion = ModelClarifyingQuestion

__all__ = [
    "ModelClarifyingQuestion",
    "ClarifyingQuestion",
]
