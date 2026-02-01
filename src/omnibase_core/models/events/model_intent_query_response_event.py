"""Event model for intent query responses.

Published in response to ModelIntentQueryRequestedEvent after the
intent data has been retrieved from the graph database.

Response Types (matching query types):
- distribution: Returns category → count mapping
- session: Returns list of intents for a session
- recent: Returns list of recent intents
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_intent_record_payload import (
    ModelIntentRecordPayload,
)
from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelIntentQueryResponseEvent", "INTENT_QUERY_RESPONSE_EVENT"]

INTENT_QUERY_RESPONSE_EVENT = "dev.omnimemory.intent.query.response.v1"


class ModelIntentQueryResponseEvent(ModelRuntimeEventBase):
    """Event published in response to an intent query request.

    Emitted by the intent query handler after retrieving data from
    the graph database.

    Attributes:
        event_type: Event type identifier for routing.
        query_id: Matches the query_id from the request event.
        query_type: Type of query that was executed.
        status: Query status - success or error.
        distribution: For distribution queries, category → count mapping.
        intents: For session/recent queries, list of intent records.
        total_count: Total number of results (before limit).
        execution_time_ms: Query execution time in milliseconds.
        responded_at: UTC timestamp when the response was generated.
        error_message: Error details if status is 'error'.
    """

    event_type: str = Field(
        default=INTENT_QUERY_RESPONSE_EVENT,
        description="Event type identifier",
    )
    query_id: UUID = Field(
        default=...,
        description="Matches the query_id from the request event",
    )
    query_type: Literal["distribution", "session", "recent"] = Field(
        default=...,
        description="Type of query that was executed",
    )
    status: Literal["success", "error", "not_found", "no_results"] = Field(
        default="success",
        description="Query status",
    )
    distribution: dict[str, int] = Field(
        default_factory=dict,
        description="For distribution queries, category → count mapping",
    )
    intents: list[ModelIntentRecordPayload] = Field(
        default_factory=list,
        description="For session/recent queries, list of intent records",
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total number of results",
    )
    total_intents: int = Field(
        default=0,
        ge=0,
        description="For distribution queries, total intents across categories",
    )
    time_range_hours: int = Field(
        default=24,
        ge=1,
        description="Time range that was queried",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Query execution time in milliseconds",
    )
    responded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the response was generated (UTC)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if status is 'error'",
    )

    @classmethod
    def create_distribution_response(
        cls,
        query_id: UUID,
        distribution: dict[str, int],
        *,
        time_range_hours: int = 24,
        execution_time_ms: float = 0.0,
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryResponseEvent:
        """Factory method for creating a distribution query response."""
        total = sum(distribution.values())
        return cls(
            query_id=query_id,
            query_type="distribution",
            status="success",
            distribution=distribution,
            total_intents=total,
            time_range_hours=time_range_hours,
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id,
        )

    @classmethod
    def create_session_response(
        cls,
        query_id: UUID,
        intents: list[ModelIntentRecordPayload],
        *,
        execution_time_ms: float = 0.0,
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryResponseEvent:
        """Factory method for creating a session query response."""
        return cls(
            query_id=query_id,
            query_type="session",
            status="success" if intents else "no_results",
            intents=intents,
            total_count=len(intents),
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id,
        )

    @classmethod
    def create_recent_response(
        cls,
        query_id: UUID,
        intents: list[ModelIntentRecordPayload],
        *,
        time_range_hours: int = 1,
        execution_time_ms: float = 0.0,
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryResponseEvent:
        """Factory method for creating a recent intents query response."""
        return cls(
            query_id=query_id,
            query_type="recent",
            status="success" if intents else "no_results",
            intents=intents,
            total_count=len(intents),
            time_range_hours=time_range_hours,
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id,
        )

    @classmethod
    def from_error(
        cls,
        query_id: UUID,
        query_type: Literal["distribution", "session", "recent"],
        error_message: str,
        *,
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryResponseEvent:
        """Factory method for creating an error response."""
        return cls(
            query_id=query_id,
            query_type=query_type,
            status="error",
            error_message=error_message,
            correlation_id=correlation_id,
        )
