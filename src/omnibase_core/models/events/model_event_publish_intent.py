"""
Event publish intent model for coordination I/O.

This module defines the intent event used for coordinating event publishing
between nodes without performing direct domain I/O.

Pattern:
    Node (builds intent) -> Kafka (intent topic) -> IntentExecutor -> Kafka (domain topic)

Example:
    # Reducer publishes intent instead of direct event (typed payload)
    from uuid import uuid4

    from omnibase_core.constants import (
        DOMAIN_REGISTRATION,
        TOPIC_EVENT_PUBLISH_INTENT,
        TOPIC_TYPE_EVENTS,
        topic_name,
    )
    from omnibase_core.enums.enum_node_kind import EnumNodeKind
    from omnibase_core.models.events.model_node_registered_event import (
        ModelNodeRegisteredEvent,
    )

    # Example 1: Using topic_name() for dynamic topic generation
    # This creates "onex.registration.events"
    registration_topic = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_EVENTS)

    # Example 2: Create typed payload with all required fields
    node_id = uuid4()
    payload = ModelNodeRegisteredEvent(
        node_id=node_id,
        node_name="my_compute_node",
        node_type=EnumNodeKind.COMPUTE,
    )

    # Build intent with typed payload
    intent = ModelEventPublishIntent(
        correlation_id=uuid4(),
        created_by="registration_reducer_v1_0_0",
        target_topic=registration_topic,  # Use the dynamically generated topic
        target_key=str(node_id),
        target_event_type="NODE_REGISTERED",
        target_event_payload=payload,
    )

    # Publish to intent topic for execution by IntentExecutor
    await publish_to_kafka(TOPIC_EVENT_PUBLISH_INTENT, intent)

Note:
    TOPIC_EVENT_PUBLISH_INTENT is defined in constants_topic_taxonomy.py and
    should be imported from omnibase_core.constants. Use topic_name() to generate
    domain-specific topic names dynamically.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
        from uuid import uuid4

        from omnibase_core.constants import TOPIC_REGISTRATION_EVENTS
        from omnibase_core.enums.enum_node_kind import EnumNodeKind
        from omnibase_core.models.events.model_node_registered_event import (
            ModelNodeRegisteredEvent,
        )

        node_id = uuid4()
        payload = ModelNodeRegisteredEvent(
            node_id=node_id,
            node_name="my_service",
            node_type=EnumNodeKind.COMPUTE,
        )
        intent = ModelEventPublishIntent(
            correlation_id=uuid4(),
            created_by="my_node_v1",
            target_topic=TOPIC_REGISTRATION_EVENTS,
            target_key=str(node_id),
            target_event_type="NODE_REGISTERED",
            target_event_payload=payload,
        )
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("target_event_payload", mode="before")
    @classmethod
    def _reject_dict_with_helpful_error(cls, v: object) -> object:
        """
        Reject dict payloads with clear migration guidance.

        As of v0.4.0, dict[str, Any] payloads are no longer supported.
        This validator provides a helpful error message explaining:
        1. What went wrong
        2. Why it changed
        3. How to fix it

        Args:
            v: The value being validated for target_event_payload.

        Returns:
            The unmodified value if it's not a dict.

        Raises:
            ValueError: If the value is a dict, with migration guidance.
        """
        if isinstance(v, dict):
            # Build a helpful error message with migration guidance
            raise ValueError(
                "dict[str, Any] payloads are no longer supported (removed in v0.4.0). "
                "Use typed payloads from ModelEventPayloadUnion instead.\n\n"
                "Migration example:\n"
                "  # Before (no longer works):\n"
                "  target_event_payload={'node_id': '...', 'name': '...'}\n\n"
                "  # After (required):\n"
                "  from omnibase_core.models.events.model_node_registered_event import (\n"
                "      ModelNodeRegisteredEvent,\n"
                "  )\n"
                "  target_event_payload=ModelNodeRegisteredEvent(\n"
                "      node_id=uuid4(),\n"
                "      node_name='my_node',\n"
                "      node_type=EnumNodeKind.COMPUTE,\n"
                "  )\n\n"
                "Available payload types:\n"
                "  - ModelNodeRegisteredEvent (node lifecycle)\n"
                "  - ModelNodeUnregisteredEvent (node lifecycle)\n"
                "  - ModelSubscriptionCreatedEvent (subscriptions)\n"
                "  - ModelSubscriptionFailedEvent (subscriptions)\n"
                "  - ModelSubscriptionRemovedEvent (subscriptions)\n"
                "  - ModelRuntimeReadyEvent (runtime status)\n"
                "  - ModelNodeGraphReadyEvent (runtime status)\n"
                "  - ModelWiringResultEvent (wiring)\n"
                "  - ModelWiringErrorEvent (wiring)\n\n"
                "See: docs/architecture/PAYLOAD_TYPE_ARCHITECTURE.md\n"
                "Import: from omnibase_core.models.events.payloads import ModelEventPayloadUnion"
            )
        return v

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Ensure forward references are resolved when subclassing.

        This hook automatically invokes _rebuild_model() when a subclass is
        created, ensuring that ModelEventPayloadUnion and ModelRetryPolicy
        forward references are properly resolved for the subclass.

        Args:
            **kwargs: Additional keyword arguments passed to parent class.
        """
        from omnibase_core.utils.util_forward_reference_resolver import (
            handle_subclass_forward_refs,
        )

        super().__init_subclass__(**kwargs)
        handle_subclass_forward_refs(
            parent_model=ModelEventPublishIntent,
            subclass=cls,
            rebuild_func=_rebuild_model,
        )

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
        examples=["dev.omninode-bridge.registration.events.v1"],
    )
    target_key: str = Field(
        ...,
        description="Kafka key for the target event",
    )
    target_event_type: str = Field(
        ...,
        description="Event type name (for routing and logging)",
        examples=["NODE_REGISTERED", "NODE_UNREGISTERED"],
    )
    target_event_payload: ModelEventPayloadUnion = Field(
        ...,
        description="Event payload to publish. Must be a typed payload from ModelEventPayloadUnion.",
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

    Raises:
        ModelOnexError: If imports fail or model rebuild fails due to
            missing dependencies or configuration issues.
    """
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError
    from omnibase_core.utils.util_forward_reference_resolver import (
        rebuild_model_references,
    )

    try:
        # Lazy imports to avoid circular dependency during module load
        from omnibase_core.models.events.payloads import ModelEventPayloadUnion
        from omnibase_core.models.infrastructure.model_retry_policy import (
            ModelRetryPolicy,
        )
    except ImportError as e:
        raise ModelOnexError(
            message=f"Failed to import required modules for model rebuild: {e}",
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
            context={
                "model": "ModelEventPublishIntent",
                "missing_module": str(e),
            },
        ) from e

    # Delegate to the shared forward reference resolver utility
    rebuild_model_references(
        model_class=ModelEventPublishIntent,
        type_mappings={
            "ModelEventPayloadUnion": ModelEventPayloadUnion,
            "ModelRetryPolicy": ModelRetryPolicy,
        },
    )


# Automatic forward reference resolution
# =====================================
# Invoke _rebuild_model() automatically on module load to resolve
# TYPE_CHECKING forward references. This ensures typed payload validation
# works correctly without requiring manual intervention.

from omnibase_core.utils.util_forward_reference_resolver import (
    auto_rebuild_on_module_load,
)

auto_rebuild_on_module_load(
    rebuild_func=_rebuild_model,
    model_name="ModelEventPublishIntent",
)
