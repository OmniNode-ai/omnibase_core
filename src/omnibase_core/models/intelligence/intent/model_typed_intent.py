# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Classified, structured intent model.

Represents a single classified user intent produced by the Intent Intelligence
Framework. This is the primary cross-repo data structure for conveying intent
classification results between classification, drift detection, and forecasting
subsystems.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

__all__ = ["ModelTypedIntent"]


class ModelTypedIntent(BaseModel):
    """Classified, structured intent object.

    Captures the result of intent classification for a single user prompt
    within a session. Immutable after creation to ensure safe cross-service
    transmission.

    Attributes:
        intent_id: Unique identifier for this classified intent.
        intent_class: The classified intent class (REFACTOR, BUGFIX, etc.).
        session_id: Session in which the intent was produced.
        prompt_preview: Truncated preview of the original prompt (max 100 chars).
            Must not contain secrets or PII beyond what is safe for observability.
        confidence_score: Classification confidence score in [0.0, 1.0].
        classified_at: Timestamp when classification was performed (UTC).
            Callers must inject this value; no ``datetime.now()`` defaults.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import UTC, datetime
        >>> from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
        >>> intent = ModelTypedIntent(
        ...     intent_id=uuid4(),
        ...     intent_class=EnumIntentClass.BUGFIX,
        ...     session_id="session-abc",
        ...     prompt_preview="Fix the null pointer exception in...",
        ...     confidence_score=0.92,
        ...     classified_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    intent_id: UUID = Field(
        description="Unique identifier for this classified intent",
    )
    intent_class: EnumIntentClass = Field(
        description="The classified intent class (REFACTOR, BUGFIX, FEATURE, etc.)",
    )
    # string-id-ok: External session ID (Claude Code, CLI, etc.), not ONEX-internal UUID
    session_id: str = Field(
        description="Session in which the intent was produced",
    )
    prompt_preview: str = Field(
        max_length=100,
        description=(
            "Truncated preview of the original prompt (max 100 chars). "
            "Must not contain secrets or PII beyond what is safe for observability."
        ),
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score in [0.0, 1.0]",
    )
    classified_at: datetime = Field(
        description=(
            "Timestamp when classification was performed (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )
