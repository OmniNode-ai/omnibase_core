"""Event model for intent query requests.

Published when a client (e.g., dashboard) requests intent data via events
rather than direct database queries. This enables event-driven architecture
where the dashboard doesn't directly connect to Memgraph.

Query Types:
- distribution: Get intent category counts for a time range
- session: Get intents for a specific session
- recent: Get recent intents across all sessions
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelIntentQueryRequestedEvent", "INTENT_QUERY_REQUESTED_EVENT"]

INTENT_QUERY_REQUESTED_EVENT = "dev.omnimemory.intent.query.requested.v1"


class ModelIntentQueryRequestedEvent(ModelRuntimeEventBase):
    """Event published when a client requests intent data.

    Emitted by dashboard or other clients to request intent information
    via the event bus rather than direct database queries.

    Attributes:
        event_type: Event type identifier for routing.
        query_id: Unique identifier for this query request.
        query_type: Type of query (distribution, session, or recent).
        session_ref: For session queries, the target session reference.
        time_range_hours: For distribution queries, the lookback period.
        min_confidence: Minimum confidence threshold for filtering.
        limit: Maximum number of results to return.
        requester_name: Name of the requesting client/service.
        requested_at: UTC timestamp when the query was requested.
    """

    event_type: str = Field(
        default=INTENT_QUERY_REQUESTED_EVENT,
        description="Event type identifier",
    )
    query_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this query request",
    )
    query_type: Literal["distribution", "session", "recent"] = Field(
        default=...,
        description="Type of query: 'distribution', 'session', or 'recent'",
    )
    session_ref: str | None = Field(
        default=None,
        description="For session queries, the target session reference",
    )
    time_range_hours: int = Field(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="For distribution/recent queries, lookback period in hours",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for filtering",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return",
    )
    requester_name: str = Field(
        default="unknown",
        description="Name of the requesting client/service",
    )
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the query was requested (UTC)",
    )

    @classmethod
    def create_distribution_query(
        cls,
        *,
        time_range_hours: int = 24,
        min_confidence: float = 0.0,
        requester_name: str = "omnidash",
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryRequestedEvent:
        """Factory method for creating a distribution query request."""
        return cls(
            query_type="distribution",
            time_range_hours=time_range_hours,
            min_confidence=min_confidence,
            requester_name=requester_name,
            correlation_id=correlation_id,
        )

    @classmethod
    def create_session_query(
        cls,
        session_ref: str,
        *,
        min_confidence: float = 0.0,
        limit: int = 100,
        requester_name: str = "omnidash",
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryRequestedEvent:
        """Factory method for creating a session query request."""
        return cls(
            query_type="session",
            session_ref=session_ref,
            min_confidence=min_confidence,
            limit=limit,
            requester_name=requester_name,
            correlation_id=correlation_id,
        )

    @classmethod
    def create_recent_query(
        cls,
        *,
        time_range_hours: int = 1,
        min_confidence: float = 0.0,
        limit: int = 50,
        requester_name: str = "omnidash",
        correlation_id: UUID | None = None,
    ) -> ModelIntentQueryRequestedEvent:
        """Factory method for creating a recent intents query request."""
        return cls(
            query_type="recent",
            time_range_hours=time_range_hours,
            min_confidence=min_confidence,
            limit=limit,
            requester_name=requester_name,
            correlation_id=correlation_id,
        )
