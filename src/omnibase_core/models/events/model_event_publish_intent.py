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
        TOPIC_EVENT_PUBLISH_INTENT,
        TOPIC_REGISTRATION_EVENTS,
        TOPIC_TYPE_EVENTS,
        topic_name,
    )
    from omnibase_core.enums.enum_node_kind import EnumNodeKind
    from omnibase_core.models.events.model_node_registered_event import (
        ModelNodeRegisteredEvent,
    )

    # Example 1: Using pre-defined topic constants (preferred)
    # TOPIC_REGISTRATION_EVENTS = "onex.registration.events"
    node_id = uuid4()
    payload = ModelNodeRegisteredEvent(
        node_id=node_id,
        node_name="my_compute_node",
        node_type=EnumNodeKind.COMPUTE,
    )
    intent = ModelEventPublishIntent(
        correlation_id=uuid4(),
        created_by="registration_reducer_v1_0_0",
        target_topic=TOPIC_REGISTRATION_EVENTS,  # Use pre-defined constant
        target_key=str(node_id),
        target_event_type="NODE_REGISTERED",
        target_event_payload=payload,
    )

    # Example 2: Using topic_name() for dynamic topic generation
    # Use when you need a custom domain topic (e.g., service-specific domains)
    from omnibase_core.models.events.model_runtime_ready_event import (
        ModelRuntimeReadyEvent,
    )

    custom_domain_topic = topic_name("my-service", TOPIC_TYPE_EVENTS)
    # Creates "onex.my-service.events"

    runtime_payload = ModelRuntimeReadyEvent(
        runtime_id=uuid4(),
        node_count=5,
        subscription_count=10,
        event_bus_type="kafka",
    )
    custom_intent = ModelEventPublishIntent(
        correlation_id=uuid4(),
        created_by="custom_service_v1_0_0",
        target_topic=custom_domain_topic,  # Use dynamically generated topic
        target_key=str(uuid4()),
        target_event_type="RUNTIME_READY",
        target_event_payload=runtime_payload,
    )

    # Publish to intent topic for execution by IntentExecutor
    await publish_to_kafka(TOPIC_EVENT_PUBLISH_INTENT, custom_intent)

    # Example 3: Using TOPIC_METRICS_EVENTS for node health metrics
    # Health events can be published to the metrics domain topic for monitoring
    from omnibase_core.constants import TOPIC_METRICS_EVENTS
    from omnibase_core.models.events.payloads import ModelNodeHealthEvent

    node_id = uuid4()
    health_payload = ModelNodeHealthEvent.create_healthy_report(
        node_id=node_id,
        node_name="worker-node-01",
        uptime_seconds=3600,
        response_time_ms=25.5,
    )
    metrics_intent = ModelEventPublishIntent(
        correlation_id=uuid4(),
        created_by="health_monitor_v1_0_0",
        target_topic=TOPIC_METRICS_EVENTS,  # Use pre-defined metrics topic
        target_key=str(node_id),
        target_event_type="NODE_HEALTH",
        target_event_payload=health_payload,
    )
    await publish_to_kafka(TOPIC_EVENT_PUBLISH_INTENT, metrics_intent)

Note:
    TOPIC_EVENT_PUBLISH_INTENT is defined in constants_topic_taxonomy.py and
    should be imported from omnibase_core.constants. Use pre-defined topic
    constants (e.g., TOPIC_REGISTRATION_EVENTS, TOPIC_METRICS_EVENTS) when
    available, or use topic_name() to generate domain-specific topic names
    dynamically.
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

    Automatic Invocation:
        **In most cases, you do NOT need to call this function manually.**

        This function is automatically invoked in two scenarios:

        1. **Module Load**: When this module is first imported,
           ``auto_rebuild_on_module_load()`` is called at module level,
           which triggers ``_rebuild_model()`` to resolve forward references.

        2. **Subclassing**: When a class inherits from ModelEventPublishIntent,
           the ``__init_subclass__`` hook calls ``handle_subclass_forward_refs()``,
           which invokes ``_rebuild_model()`` to ensure the subclass has
           resolved forward references.

        These automatic mechanisms ensure that ModelEventPublishIntent works
        correctly out of the box without manual intervention.

    When to Call Manually:
        You may need to call this function explicitly only in rare edge cases:

        - **Testing isolation**: When running tests that mock dependencies,
          you may need to call ``_rebuild_model()`` to reset the model state.
        - **Hot reloading**: When using development servers that reload modules,
          calling ``_rebuild_model()`` ensures forward references are resolved
          after the reload.
        - **Debugging**: When debugging forward reference issues, explicitly
          calling this function can help identify where the problem occurs.

    Why This Exists:
        ModelEventPublishIntent uses TYPE_CHECKING imports to avoid circular
        dependencies with ModelEventPayloadUnion and ModelRetryPolicy. These
        forward references need explicit resolution before the model can
        properly validate typed payloads.

    Example:
        >>> # Typically not needed - automatic resolution handles this
        >>> from omnibase_core.models.events.model_event_publish_intent import (
        ...     ModelEventPublishIntent,
        ... )
        >>> # Just use the model directly - forward refs are already resolved
        >>> intent = ModelEventPublishIntent(...)
        >>>
        >>> # Only call _rebuild_model() for debugging or testing:
        >>> from omnibase_core.models.events.model_event_publish_intent import (
        ...     _rebuild_model,
        ... )
        >>> _rebuild_model()  # Explicit rebuild (rarely needed)

    Note:
        This pattern is common in Pydantic models that use TYPE_CHECKING
        imports. The model_rebuild() call injects the actual types into
        Pydantic's type resolution namespace.

    Raises:
        ModelOnexError: If imports fail or model rebuild fails due to
            missing dependencies or configuration issues. Specific error codes:

            - **IMPORT_ERROR**: Required modules (payloads, retry_policy)
              are not yet available. This typically occurs during early
              bootstrap when module loading order prevents imports.
            - **INITIALIZATION_FAILED**: Schema generation or type resolution
              failed. This indicates invalid type annotations or incompatible
              type constraints in the model definition.
            - **CONFIGURATION_ERROR**: Invalid Pydantic model configuration.
              This indicates problems with ConfigDict options or conflicting
              field definitions.
    """
    # Import error handling utilities first - these are core dependencies
    # that should always be available after initial bootstrap
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError
    from omnibase_core.utils.util_forward_reference_resolver import (
        rebuild_model_references,
    )

    # Import payload types - these may fail during early bootstrap
    try:
        from omnibase_core.models.events.payloads import ModelEventPayloadUnion
        from omnibase_core.models.infrastructure.model_retry_policy import (
            ModelRetryPolicy,
        )
    except ImportError as e:
        raise ModelOnexError(
            message=f"Failed to import payload types for ModelEventPublishIntent: {e}",
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
            context={
                "model": "ModelEventPublishIntent",
                "missing_module": str(e),
                "hint": "Ensure omnibase_core.models.events.payloads is importable",
            },
        ) from e

    # Rebuild model with resolved types
    #
    # The utility function handles Pydantic-specific errors and raises
    # ModelOnexError with appropriate error codes (INITIALIZATION_FAILED,
    # CONFIGURATION_ERROR). We handle specific exception types here:
    #
    # - ModelOnexError: Re-raised as-is (already has proper error codes)
    # - TypeError/ValueError: Wrapped with context (type annotation issues)
    # - AttributeError: Wrapped with context (module/attribute issues)
    # - RuntimeError: Wrapped with context (module manipulation failures)
    #
    # NOTE: We intentionally DO NOT use `except Exception` to avoid masking
    # unexpected errors. Unknown exceptions should propagate for debugging.
    try:
        rebuild_model_references(
            model_class=ModelEventPublishIntent,
            type_mappings={
                "ModelEventPayloadUnion": ModelEventPayloadUnion,
                "ModelRetryPolicy": ModelRetryPolicy,
            },
        )
    except ModelOnexError:
        # Re-raise ModelOnexError as-is - already has proper error codes
        raise
    except (TypeError, ValueError) as e:
        # Type annotation or value issues not caught by utility
        raise ModelOnexError(
            message=f"Type error during ModelEventPublishIntent rebuild: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "hint": "Check type annotations and model configuration",
            },
        ) from e
    except AttributeError as e:
        # Module or attribute access issues
        raise ModelOnexError(
            message=f"Attribute error during ModelEventPublishIntent rebuild: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": "AttributeError",
                "error_details": str(e),
                "hint": "Check module loading and attribute access",
            },
        ) from e
    except RuntimeError as e:
        # RuntimeError during module manipulation is a critical failure
        raise ModelOnexError(
            message=f"Runtime error during ModelEventPublishIntent rebuild: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": "RuntimeError",
                "error_details": str(e),
                "hint": "Check for module manipulation issues or circular imports",
            },
        ) from e


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
