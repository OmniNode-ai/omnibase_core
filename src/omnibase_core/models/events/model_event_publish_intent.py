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
    # This creates "dev.omninode-bridge.registration.events.v1"
    registration_topic = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_EVENTS)

    # Example 2: Create typed payload with all required fields
    node_id = uuid4()
    payload = ModelNodeRegisteredEvent(
        node_id=node_id,
        node_name="my_compute_node",
        node_type=EnumNodeKind.COMPUTE,
    )

    # Build intent with typed payload (recommended over dict[str, Any])
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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Ensure forward references are resolved when subclassing.

        This hook automatically invokes _rebuild_model() when a subclass is
        created, ensuring that ModelEventPayloadUnion and ModelRetryPolicy
        forward references are properly resolved for the subclass.

        Args:
            **kwargs: Additional keyword arguments passed to parent class.
        """
        import logging
        import warnings

        super().__init_subclass__(**kwargs)
        _logger = logging.getLogger(__name__)

        # Attempt to rebuild the model to resolve forward references
        # This ensures subclasses inherit properly resolved types
        try:
            _rebuild_model()
        except ImportError as e:
            # Dependencies not yet available during early loading
            # This is expected during bootstrap - Pydantic will lazily resolve
            _logger.debug(
                "ModelEventPublishIntent subclass %s: forward reference rebuild "
                "deferred (ImportError during bootstrap): %s",
                cls.__name__,
                e,
            )
        except (TypeError, ValueError) as e:
            # Type annotation issues during rebuild - likely configuration error
            _msg = (
                f"ModelEventPublishIntent subclass {cls.__name__}: forward reference "
                f"rebuild failed ({type(e).__name__}): {e}. "
                f"Call _rebuild_model() explicitly after all dependencies are loaded."
            )
            _logger.warning(_msg)
            warnings.warn(_msg, UserWarning, stacklevel=2)

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
    target_event_payload: (
        ModelEventPayloadUnion
        | dict[str, Any]  # ONEX_EXCLUDE: dict_str_any - union with typed payloads
    ) = Field(
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

    Raises:
        ModelOnexError: If imports fail or model rebuild fails due to
            missing dependencies or configuration issues.
    """
    import sys

    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

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

    try:
        # Import Pydantic-specific exceptions for precise error handling
        from pydantic import PydanticSchemaGenerationError, PydanticUserError
    except ImportError:
        # Fallback for older Pydantic versions
        PydanticSchemaGenerationError = TypeError  # type: ignore[misc, assignment]
        PydanticUserError = ValueError  # type: ignore[misc, assignment]

    try:
        # Inject types into module globals for Pydantic to resolve forward references
        current_module = sys.modules[__name__]
        setattr(current_module, "ModelEventPayloadUnion", ModelEventPayloadUnion)
        setattr(current_module, "ModelRetryPolicy", ModelRetryPolicy)

        # Rebuild model with resolved types namespace
        ModelEventPublishIntent.model_rebuild(
            _types_namespace={
                "ModelEventPayloadUnion": ModelEventPayloadUnion,
                "ModelRetryPolicy": ModelRetryPolicy,
            }
        )
    except PydanticSchemaGenerationError as e:
        # Schema generation failed due to invalid type annotations
        raise ModelOnexError(
            message=f"Failed to generate schema for ModelEventPublishIntent: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": "PydanticSchemaGenerationError",
                "error_details": str(e),
            },
        ) from e
    except PydanticUserError as e:
        # User configuration error in Pydantic model definition
        raise ModelOnexError(
            message=f"Invalid Pydantic configuration for ModelEventPublishIntent: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": "PydanticUserError",
                "error_details": str(e),
            },
        ) from e
    except (TypeError, ValueError) as e:
        # TypeError: Invalid type annotations or type parameters
        # ValueError: General validation/schema issues
        raise ModelOnexError(
            message=f"Failed to rebuild ModelEventPublishIntent: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        ) from e
    except AttributeError as e:
        # Module attribute access issues during rebuild
        raise ModelOnexError(
            message=f"Attribute error during ModelEventPublishIntent rebuild: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": "ModelEventPublishIntent",
                "error_type": "AttributeError",
                "error_details": str(e),
            },
        ) from e


# Automatic forward reference resolution
# =====================================
# Invoke _rebuild_model() automatically on module load to resolve
# TYPE_CHECKING forward references. This ensures typed payload validation
# works correctly without requiring manual intervention.


def _log_rebuild_failure(
    error_code_str: str, error_msg: str, error_type: str | None = None
) -> None:
    """Log and warn about rebuild failure in a consistent format."""
    import logging as _logging
    import warnings as _warnings

    _full_msg = (
        f"ModelEventPublishIntent: automatic forward reference rebuild failed"
        f"{f' ({error_type})' if error_type else ''}: "
        f"{error_code_str}: {error_msg}. "
        f"Call _rebuild_model() explicitly after all dependencies are loaded."
    )

    _logger = _logging.getLogger(__name__)
    _logger.warning(_full_msg)
    _warnings.warn(_full_msg, UserWarning, stacklevel=3)


try:
    # Import ModelOnexError for specific exception handling
    from omnibase_core.models.errors.model_onex_error import (
        ModelOnexError as _ModelOnexError,
    )

    try:
        _rebuild_model()
    except _ModelOnexError as _rebuild_error:
        # Structured error from _rebuild_model() - extract details for logging
        # ModelOnexError has error_code: EnumOnexErrorCode | str | None
        _error_code = _rebuild_error.error_code
        if _error_code is None:
            _error_code_str = "UNKNOWN"
        elif hasattr(_error_code, "value"):
            _error_code_str = str(_error_code.value)  # type: ignore[union-attr]
        else:
            _error_code_str = str(_error_code)
        _error_msg = _rebuild_error.message or str(_rebuild_error)
        _log_rebuild_failure(_error_code_str, _error_msg, "ModelOnexError")
    except (TypeError, ValueError, AttributeError) as _type_error:
        # Specific exception types that could escape _rebuild_model()
        # These are recoverable - Pydantic will lazily resolve on first use
        _log_rebuild_failure(
            type(_type_error).__name__,
            str(_type_error),
            "type_error",
        )
    except RuntimeError as _runtime_error:
        # RuntimeError could occur during module manipulation
        _log_rebuild_failure(
            "RUNTIME_ERROR",
            str(_runtime_error),
            "RuntimeError",
        )
except ImportError as _import_error:
    # Handle case where ModelOnexError itself fails to import (early bootstrap)
    # This is expected during early module loading before all dependencies exist
    # Use _log_rebuild_failure for consistent error handling pattern
    _log_rebuild_failure(
        error_code_str="IMPORT_ERROR",
        error_msg=str(_import_error),
        error_type="ImportError (bootstrap)",
    )
