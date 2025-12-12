"""
Event publish intent model for coordination I/O.

This module defines the intent event used for coordinating event publishing
between nodes without performing direct domain I/O.

Pattern:
    Node (builds intent) → Kafka (intent topic) → IntentExecutor → Kafka (domain topic)

Example:
    # Reducer publishes intent instead of direct event
    intent = ModelEventPublishIntent(
        target_topic=TOPIC_METRICS_RECORDED,
        target_event=metrics_event
    )
    await publish_to_kafka(TOPIC_EVENT_PUBLISH_INTENT, intent)
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any

# Kafka topic for intent events
TOPIC_EVENT_PUBLISH_INTENT = "dev.omninode-bridge.intents.event-publish.v1"


@allow_dict_str_any(
    "Event publish intent requires flexible target_event_payload to carry "
    "arbitrary event data for domain events being published to Kafka."
)
class ModelEventPublishIntent(BaseModel):
    """
    Intent to publish an event to Kafka.

    This is a coordination event that instructs an intent executor
    to publish a domain event to its target topic. This allows nodes
    to coordinate actions without performing direct I/O.

    Attributes:
        intent_id: Unique identifier for this intent
        correlation_id: Correlation ID for tracing
        created_at: When intent was created (UTC)
        created_by: Service/node that created this intent
        target_topic: Kafka topic where event should be published
        target_key: Kafka key for the target event
        target_event_type: Event type name (for routing/logging)
        target_event_payload: Event payload to publish
        priority: Intent priority (1=highest, 10=lowest)
        retry_policy: Optional retry configuration
    """

    model_config = ConfigDict(extra="forbid")

    # Intent metadata
    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracing through workflow",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When intent was created (UTC)",
    )
    created_by: str = Field(
        ...,
        description="Service/node that created this intent",
        examples=["metrics_reducer_v1_0_0", "orchestrator_v1_0_0"],
    )

    # Target event details
    target_topic: str = Field(
        ...,
        description="Kafka topic where event should be published",
        examples=["dev.omninode-bridge.codegen.metrics-recorded.v1"],
    )
    target_key: str = Field(
        ...,
        description="Kafka key for the target event",
    )
    target_event_type: str = Field(
        ...,
        description="Event type name (for routing and logging)",
        examples=["GENERATION_METRICS_RECORDED", "NODE_GENERATION_COMPLETED"],
    )
    target_event_payload: dict[str, Any] = Field(
        ...,
        description="Event payload to publish (already serialized to dict)",
    )

    # Execution hints
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Intent priority (1=highest, 10=lowest)",
    )
    retry_policy: dict[str, Any] | None = Field(
        default=None,
        description="Optional retry configuration for intent execution",
    )
