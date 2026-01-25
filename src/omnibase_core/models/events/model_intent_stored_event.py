"""Event model for intent storage completion.

Published when an intent classification has been successfully stored
in the graph database (Memgraph) by the intent_storage_effect node.

This event enables downstream consumers to:
- Update real-time dashboards with new intent data
- Trigger analytics aggregation jobs
- Maintain audit trails of intent storage operations
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelIntentStoredEvent", "INTENT_STORED_EVENT"]

INTENT_STORED_EVENT = "dev.omnimemory.intent.stored.v1"


class ModelIntentStoredEvent(ModelRuntimeEventBase):
    """Event published when an intent classification is stored.

    Emitted by the intent_storage_effect node after successfully
    persisting an intent classification to the graph database.

    Attributes:
        event_type: Event type identifier for routing.
        intent_id: Unique identifier for the stored intent node.
        session_ref: Session reference the intent is linked to.
        intent_category: The classified intent category.
        confidence: Confidence score from the classification.
        keywords: Keywords associated with the intent.
        created: True if new intent created, False if merged.
        stored_at: UTC timestamp when the intent was stored.
        execution_time_ms: Storage operation time in milliseconds.
    """

    event_type: str = Field(
        default=INTENT_STORED_EVENT,
        description="Event type identifier",
    )
    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the stored intent node",
    )
    session_ref: str = Field(
        default=...,
        min_length=1,
        description="Session reference the intent is linked to",
    )
    intent_category: str = Field(
        default=...,
        min_length=1,
        description="The classified intent category (e.g., 'debugging', 'code_generation')",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords associated with the intent",
    )
    created: bool = Field(
        default=True,
        description="True if new intent created, False if merged with existing",
    )
    stored_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the intent was stored (UTC)",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Storage operation execution time in milliseconds",
    )
    status: Literal["success", "error"] = Field(
        default="success",
        description="Storage operation status",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if status is 'error'",
    )

    @classmethod
    def create(
        cls,
        session_ref: str,
        intent_category: str,
        *,
        intent_id: UUID | None = None,
        confidence: float = 0.0,
        keywords: list[str] | None = None,
        created: bool = True,
        execution_time_ms: float = 0.0,
        correlation_id: UUID | None = None,
        source_node_id: UUID | None = None,
    ) -> ModelIntentStoredEvent:
        """Factory method for creating an intent stored event."""
        return cls(
            intent_id=intent_id or uuid4(),
            session_ref=session_ref,
            intent_category=intent_category,
            confidence=confidence,
            keywords=keywords if keywords is not None else [],
            created=created,
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id,
            source_node_id=source_node_id,
        )

    @classmethod
    def from_error(
        cls,
        session_ref: str,
        intent_category: str,
        error_message: str,
        *,
        correlation_id: UUID | None = None,
        source_node_id: UUID | None = None,
    ) -> ModelIntentStoredEvent:
        """Factory method for creating a failed intent stored event."""
        return cls(
            session_ref=session_ref,
            intent_category=intent_category,
            status="error",
            error_message=error_message,
            correlation_id=correlation_id,
            source_node_id=source_node_id,
        )
