"""
Intent publish result model for coordination I/O.

This module provides the ModelIntentPublishResult class that represents
the result of publishing an intent through the IntentPublisherMixin.
It provides full traceability for intent operations with correlation
support for distributed tracing.

Thread Safety:
    ModelIntentPublishResult is immutable after creation (Pydantic model).
    Thread-safe for concurrent read access.

Key Features:
    - Unique intent_id for operation tracking
    - Publication timestamp for ordering and debugging
    - Target topic for event routing verification
    - Correlation ID for distributed tracing

Example:
    >>> from omnibase_core.models.reducer import ModelIntentPublishResult
    >>> from datetime import datetime, timezone
    >>> from uuid import uuid4
    >>>
    >>> # Create result after publishing intent
    >>> result = ModelIntentPublishResult(
    ...     intent_id=uuid4(),
    ...     published_at=datetime.now(timezone.utc),
    ...     target_topic="user.events",
    ...     correlation_id=request_correlation_id,
    ... )
    >>>
    >>> # Use for tracing
    >>> print(f"Intent {result.intent_id} published to {result.target_topic}")

See Also:
    - omnibase_core.models.reducer.model_intent: ModelIntent being published
    - omnibase_core.mixins.mixin_intent_publisher: IntentPublisherMixin
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
