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

Migration (v0.4.0):
    - target_event_payload now accepts typed payloads (ModelEventPayloadUnion)
    - Legacy dict[str, Any] payloads still work but emit deprecation warnings
    - retry_policy now uses ModelRetryPolicy instead of dict[str, Any]
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.utils.util_decorators import allow_dict_str_any

if TYPE_CHECKING:
    from omnibase_core.models.events.payloads import ModelEventPayloadUnion
    from omnibase_core.models.infrastructure.model_retry_policy import ModelRetryPolicy


@allow_dict_str_any(
    "Event publish intent supports legacy dict[str, Any] payloads for migration "
    "support during transition to typed ModelEventPayloadUnion payloads. "
    "New code should use typed payloads from omnibase_core.models.events.payloads."
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
        target_event_payload: Event payload to publish (typed or legacy dict)
        priority: Intent priority (1=highest, 10=lowest)
        retry_policy: Optional retry configuration (ModelRetryPolicy)

    Migration Notes (v0.4.0):
        The target_event_payload field now accepts typed event payloads from
        ModelEventPayloadUnion. Legacy dict[str, Any] payloads are still
        supported during the transition period but will emit deprecation warnings.

        The retry_policy field now uses ModelRetryPolicy instead of dict[str, Any].

    Example (typed payload - recommended):
        from omnibase_core.models.events.payloads import ModelNodeRegisteredEvent

        intent = ModelEventPublishIntent(
            correlation_id=uuid4(),
            created_by="my_node_v1",
            target_topic="dev.runtime.node-registered.v1",
            target_key=str(node_id),
            target_event_type="NODE_REGISTERED",
            target_event_payload=ModelNodeRegisteredEvent(...),
        )

    Example (legacy dict - deprecated):
        intent = ModelEventPublishIntent(
            ...
            target_event_payload={"node_name": "test", "version": "1.0.0"},
        )
        # Emits: DeprecationWarning about untyped dict payload
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

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_payloads(cls, data: Any) -> Any:
        """
        Migrate legacy dict payloads and emit deprecation warnings.

        This validator checks for legacy dict[str, Any] usage in:
        - target_event_payload: Should use ModelEventPayloadUnion
        - retry_policy: Should use ModelRetryPolicy (auto-migrated if dict)

        Args:
            data: Raw input data before validation (Any type for mode="before")

        Returns:
            Potentially transformed data with legacy dicts migrated
        """
        if not isinstance(data, dict):
            return data

        # Check for legacy dict payload
        payload = data.get("target_event_payload")
        if isinstance(payload, dict) and not hasattr(payload, "model_fields"):
            # It's a plain dict, not a Pydantic model
            # Check if it looks like an untyped legacy payload
            # Typed payloads would have specific fields like 'event_type' or 'node_name'
            known_typed_fields = {
                "event_type",
                "node_name",
                "runtime_id",
                "subscription_id",
                "topic",
            }
            has_typed_marker = any(field in payload for field in known_typed_fields)

            if not has_typed_marker:
                warnings.warn(
                    "Using untyped dict for target_event_payload is deprecated. "
                    "Migrate to typed payloads from "
                    "omnibase_core.models.events.payloads.ModelEventPayloadUnion. "
                    "See ModelEventPublishIntent docstring for migration examples.",
                    DeprecationWarning,
                    stacklevel=4,
                )

        # Auto-migrate legacy retry_policy dict to ModelRetryPolicy
        retry_policy = data.get("retry_policy")
        if isinstance(retry_policy, dict) and not hasattr(retry_policy, "model_fields"):
            warnings.warn(
                "Using dict for retry_policy is deprecated. "
                "Migrate to ModelRetryPolicy. Example: "
                "ModelRetryPolicy.create_exponential_backoff(max_retries=5)",
                DeprecationWarning,
                stacklevel=4,
            )
            # Lazy import to avoid circular dependency
            from omnibase_core.models.infrastructure.model_retry_policy import (
                ModelRetryPolicy as RetryPolicyModel,
            )

            # Attempt to convert legacy dict to ModelRetryPolicy
            try:
                data["retry_policy"] = RetryPolicyModel(**retry_policy)
            except Exception:
                # If conversion fails, let Pydantic handle the validation error
                pass

        return data


def _rebuild_model() -> None:
    """
    Rebuild the model to resolve forward references.

    This is called after all imports are complete to ensure
    ModelEventPayloadUnion and ModelRetryPolicy types are resolved.
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


# Defer model rebuild to avoid circular import during module initialization
# Users should call _rebuild_model() after all dependent modules are loaded,
# or the model will be rebuilt automatically on first validation attempt
