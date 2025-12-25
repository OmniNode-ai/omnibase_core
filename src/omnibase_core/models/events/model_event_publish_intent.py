"""
Event publish intent model for coordination I/O.

This module defines the intent event used for coordinating event publishing
between nodes without performing direct domain I/O.

Pattern:
    Node (builds intent) → Kafka (intent topic) → IntentExecutor → Kafka (domain topic)

Example:
    # Reducer publishes intent instead of direct event (typed payload)
    from omnibase_core.constants import TOPIC_EVENT_PUBLISH_INTENT
    from omnibase_core.models.events.payloads import ModelNodeRegisteredEvent

    payload = ModelNodeRegisteredEvent(
        node_name="my_node",
        runtime_id=uuid4(),
        ...
    )
    intent = ModelEventPublishIntent(
        target_topic=TOPIC_METRICS_RECORDED,
        target_event_payload=payload,
        ...
    )
    await publish_to_kafka(TOPIC_EVENT_PUBLISH_INTENT, intent)

Note:
    TOPIC_EVENT_PUBLISH_INTENT is now defined in constants_topic_taxonomy.py
    and should be imported from omnibase_core.constants.

"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.models.events.payloads import ModelEventPayloadUnion
    from omnibase_core.models.infrastructure.model_retry_policy import ModelRetryPolicy


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
        target_event_payload: Event payload to publish (typed)
        priority: Intent priority (1=highest, 10=lowest)
        retry_policy: Optional retry configuration

    Example:
        from omnibase_core.models.events.payloads import ModelNodeRegisteredEvent

        intent = ModelEventPublishIntent(
            correlation_id=uuid4(),
            created_by="my_node_v1",
            target_topic="dev.runtime.node-registered.v1",
            target_key=str(node_id),
            target_event_type="NODE_REGISTERED",
            target_event_payload=ModelNodeRegisteredEvent(...),
        )
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

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
    target_event_payload: ModelEventPayloadUnion | dict[str, Any] = Field(
        ...,
        description=(
            "Event payload to publish. Accepts typed payloads from "
            "ModelEventPayloadUnion (recommended) or legacy dict[str, Any] "
            "(deprecated, emits warning)."
        ),
    )

    # Execution hints
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Intent priority (1=highest, 10=lowest)",
    )
    retry_policy: ModelRetryPolicy | None = Field(
        default=None,
        description=(
            "Optional retry configuration for intent execution. "
            "Use ModelRetryPolicy factory methods like create_simple(), "
            "create_exponential_backoff(), or create_for_http()."
        ),
    )


def _rebuild_model() -> None:
    """
    Rebuild the model to resolve forward references for typed payloads.

    This function resolves the TYPE_CHECKING forward references used by
    ModelEventPublishIntent (ModelEventPayloadUnion and ModelRetryPolicy).
    Forward references are necessary to avoid circular imports during
    module initialization.

    When to Call:
        - Call this function ONCE after your application has finished loading
          all dependent modules (e.g., during application startup).
        - If not called manually, Pydantic will attempt to resolve forward
          references on first validation, but explicit rebuild is recommended
          for predictable behavior.

    Why This Exists:
        ModelEventPublishIntent uses TYPE_CHECKING imports to avoid circular
        dependencies with ModelEventPayloadUnion and ModelRetryPolicy. These
        forward references need explicit resolution before the model can
        properly validate typed payloads.

    Example:
        >>> # In your application startup code:
        >>> from omnibase_core.models.events.model_event_publish_intent import (
        ...     ModelEventPublishIntent,
        ...     _rebuild_model,
        ... )
        >>> _rebuild_model()  # Resolve forward references
        >>>
        >>> # Now ModelEventPublishIntent can validate typed payloads
        >>> intent = ModelEventPublishIntent(...)

    Note:
        This pattern is common in Pydantic models that use TYPE_CHECKING
        imports. The model_rebuild() call injects the actual types into
        Pydantic's type resolution namespace.
    """
    # Lazy imports to avoid circular dependency during module load
    # Inject types into module globals for Pydantic to resolve forward references
    import sys

    from omnibase_core.models.events.payloads import (
        ModelEventPayloadUnion,
    )
    from omnibase_core.models.infrastructure.model_retry_policy import (
        ModelRetryPolicy,
    )

    current_module = sys.modules[__name__]
    setattr(current_module, "ModelEventPayloadUnion", ModelEventPayloadUnion)
    setattr(current_module, "ModelRetryPolicy", ModelRetryPolicy)

    # Also update the model's __pydantic_parent_namespace__
    ModelEventPublishIntent.model_rebuild(
        _types_namespace={
            "ModelEventPayloadUnion": ModelEventPayloadUnion,
            "ModelRetryPolicy": ModelRetryPolicy,
        }
    )


# Forward Reference Resolution
# ============================
# This module uses TYPE_CHECKING imports to break circular dependencies.
# As a result, forward references (ModelEventPayloadUnion, ModelRetryPolicy)
# must be resolved before typed payload validation can work correctly.
#
# Options:
#   1. Call _rebuild_model() explicitly during application startup (recommended)
#   2. Let Pydantic auto-resolve on first model_validate() call (less predictable)
#
# See _rebuild_model() docstring for detailed usage instructions.
