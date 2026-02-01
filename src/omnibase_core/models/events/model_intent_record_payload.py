"""Payload model for intent records in query responses.

Lightweight representation of a stored intent for transmission
in query response events.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_event_payload_base import (
    ModelEventPayloadBase,
)

__all__ = ["ModelIntentRecordPayload"]


class ModelIntentRecordPayload(ModelEventPayloadBase):
    """Embedded intent record in query responses.

    Lightweight representation of a stored intent for transmission
    in query response events.

    This is a payload model (inherits from ModelEventPayloadBase), not an event.
    It does NOT carry event metadata (event_id, timestamp, correlation_id).
    Event metadata belongs on the containing event envelope.

    Attributes:
        intent_id: Unique identifier for the intent.
        session_ref: Session reference the intent belongs to.
        intent_category: The classified intent category.
        confidence: Confidence score from 0.0 to 1.0.
        keywords: Keywords associated with the intent.
        created_at: When the intent was stored in the graph (domain data, not event metadata).
    """

    intent_id: UUID = Field(
        default=...,
        description="Unique identifier for the intent",
    )
    session_ref: str = Field(
        default=...,
        description="Session reference the intent belongs to",
    )
    intent_category: str = Field(
        default=...,
        description="The classified intent category",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords associated with the intent",
    )
    created_at: datetime = Field(
        default=...,
        description="When the intent was stored in the graph (UTC)",
    )
