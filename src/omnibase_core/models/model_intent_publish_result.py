"""
Intent publish result model for coordination I/O.

This model represents the result of publishing an intent through the
IntentPublisherMixin. It provides traceability for intent operations.

Part of omnibase_core framework - coordination I/O result models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelIntentPublishResult(BaseModel):
    """
    Result of publishing an intent.

    Attributes:
        intent_id: Unique identifier for the published intent
        published_at: When intent was published (UTC)
        target_topic: Topic where event will be published
        correlation_id: Correlation ID for tracing
    """

    intent_id: UUID = Field(
        ...,
        description="Unique identifier for the published intent",
    )
    published_at: datetime = Field(
        ...,
        description="When intent was published (UTC)",
    )
    target_topic: str = Field(
        ...,
        description="Topic where event will be published",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracing",
    )
