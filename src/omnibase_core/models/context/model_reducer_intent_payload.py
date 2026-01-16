"""Intent payload model for typed reducer intent data.

This module provides ModelReducerIntentPayload, a typed context model for carrying
structured data in reducer intents (FSM state transitions and side effect requests).

Intent System Context:
    The ONEX intent system uses two tiers:

    1. Core Intents (omnibase_core.models.intents):
       - Discriminated union pattern with typed payloads
       - Closed set of known intents

    2. Extension Intents (omnibase_core.models.reducer.model_intent):
       - Generic ModelIntent with flexible payload
       - Open set for plugins and extensions

    ModelReducerIntentPayload provides typed structure for extension intent payloads,
    replacing dict[str, Any] with validated fields while maintaining flexibility.

Thread Safety:
    ModelReducerIntentPayload instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - omnibase_core.models.reducer.model_intent: Extension intent model
    - omnibase_core.models.intents: Core infrastructure intents
    - omnibase_core.models.context.model_validation_context: Validation context
"""

from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from omnibase_core.types.type_serializable_value import SerializableValue

__all__ = ["ModelReducerIntentPayload"]


class ModelReducerIntentPayload(BaseModel):
    """Typed payload for reducer intents (FSM state transitions and side effects).

    This model provides structured fields for common intent payload patterns,
    enabling type-safe intent data while maintaining flexibility for extension
    workflows.

    Use Cases:
        - FSM state transition payloads
        - Side effect request data (logs, notifications, persistence)
        - Plugin and webhook intent payloads
        - Validation and transformation intent data

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        target_state: Target FSM state for state transition intents. Optional
            for non-FSM intents (e.g., logging, notifications).
        source_state: Source FSM state from which the transition originates.
            Used for transition validation and audit logging.
        trigger: Event or action that triggered this intent. Corresponds to
            FSM trigger names for state machine intents.
        entity_id: UUID identifying the entity being operated on (e.g., user_id,
            workflow_id, resource_id).
        entity_type: Type classification of the entity (e.g., "user", "workflow",
            "resource") for routing and processing.
        operation: Specific operation to perform (e.g., "create", "update",
            "delete", "validate", "transform").
        data: Core payload data as immutable key-value pairs (tuple of tuples,
            NOT a dict). Type is tuple[tuple[str, SerializableValue], ...].
            Use for intent-specific data that doesn't fit other fields.
            Use get_data_as_dict() to convert to dict when needed.
        validation_errors: List of validation error messages when the intent
            relates to validation failures or feedback.
        idempotency_key: Client-provided key for idempotent processing. Effects
            can use this to deduplicate repeated intent executions.
        timeout_ms: Timeout in milliseconds for intent execution. Effects should
            respect this timeout during side effect processing.
        retry_count: Number of times this intent has been retried. Used by
            effect nodes for retry logic and dead letter queue decisions.
        max_retries: Maximum number of retry attempts allowed for this intent.
            Effects should stop retrying when retry_count >= max_retries.

    Example:
        FSM state transition payload::

            from omnibase_core.models.context import ModelReducerIntentPayload
            from uuid import uuid4

            payload = ModelReducerIntentPayload(
                target_state="active",
                source_state="pending",
                trigger="user_verified",
                entity_id=uuid4(),
                entity_type="user",
                operation="activate",
            )

        Side effect payload (notification)::

            # Note: data is tuple of tuples, NOT a dict (immutable by design)
            payload = ModelReducerIntentPayload(
                entity_type="notification",
                operation="send",
                data=(  # tuple[tuple[str, SerializableValue], ...]
                    ("channel", "email"),
                    ("recipient", "user@example.com"),
                    ("template", "welcome_email"),
                ),
                idempotency_key="notif_12345",
                timeout_ms=5000,
            )

        Validation result payload::

            payload = ModelReducerIntentPayload(
                entity_type="validation",
                operation="report",
                validation_errors=(
                    "Field 'email' is required",
                    "Field 'age' must be >= 0",
                ),
            )

        Retry-aware payload::

            payload = ModelReducerIntentPayload(
                entity_type="webhook",
                operation="send",
                data=(("url", "https://api.example.com/hook"),),  # tuple of tuples
                retry_count=2,
                max_retries=5,
                timeout_ms=10000,
            )

    See Also:
        - ModelIntent: Extension intent container using this payload
        - ModelValidationContext: Detailed validation field context
        - ModelRetryContext: Detailed retry metadata
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    # Private cache for dict conversion - PrivateAttr allows mutation on frozen models.
    # Caching is safe because the model is frozen (immutable after creation) -
    # the data field never changes, so the dict representation is stable.
    _cached_data_dict: dict[str, SerializableValue] | None = PrivateAttr(default=None)

    # FSM transition fields
    target_state: str | None = Field(
        default=None,
        description="Target FSM state for state transition intents",
        min_length=1,
        max_length=100,
    )
    source_state: str | None = Field(
        default=None,
        description="Source FSM state from which the transition originates",
        min_length=1,
        max_length=100,
    )
    trigger: str | None = Field(
        default=None,
        description="Event or action that triggered this intent",
        min_length=1,
        max_length=100,
    )

    # Entity identification
    entity_id: UUID | None = Field(
        default=None,
        description="UUID identifying the entity being operated on",
    )
    entity_type: str | None = Field(
        default=None,
        description="Type classification of the entity (e.g., 'user', 'workflow')",
        min_length=1,
        max_length=100,
    )
    operation: str | None = Field(
        default=None,
        description="Specific operation to perform (e.g., 'create', 'update', 'delete')",
        min_length=1,
        max_length=100,
    )

    # Core data payload
    data: tuple[tuple[str, SerializableValue], ...] = Field(
        default=(),
        description="Core payload data as immutable key-value pairs",
    )

    # Validation feedback
    validation_errors: tuple[str, ...] = Field(
        default=(),
        description="List of validation error messages",
    )

    # Execution control
    idempotency_key: str | None = Field(
        default=None,
        description="Key for idempotent operations (duplicates with same key are deduplicated)",
        min_length=1,
        max_length=256,
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Timeout in milliseconds for intent execution",
        ge=0,
    )

    # Retry configuration
    retry_count: int = Field(
        default=0,
        description="Number of times this intent has been retried",
        ge=0,
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts allowed",
        ge=0,
    )

    def _get_cached_data_dict(self) -> dict[str, SerializableValue]:
        """Get or create the cached dict conversion of the data field.

        This internal method manages the cache for dict conversions. Caching is
        safe because the model is frozen (immutable) - the data field never
        changes after construction, so the dict representation is stable.

        Returns:
            dict[str, SerializableValue]: The cached dict (do not mutate directly).
        """
        if self._cached_data_dict is None:
            self._cached_data_dict = dict(self.data)
        return self._cached_data_dict

    @property
    def data_as_dict(self) -> Mapping[str, SerializableValue]:
        """Cached read-only view of data as a dict.

        Returns a read-only mapping view of the cached dict conversion.
        For high-performance read-only access in tight loops where mutation
        is not needed. The returned MappingProxyType prevents accidental
        mutation of the cached data.

        Caching is safe because the model is frozen (immutable after creation).

        Returns:
            Mapping[str, SerializableValue]: Read-only view of the data dict.

        See Also:
            get_data_as_dict: Returns a mutable copy if mutation is needed.

        Example:
            >>> payload = ModelReducerIntentPayload(data=(("key", "value"),))
            >>> payload.data_as_dict["key"]
            'value'
            >>> payload.data_as_dict["key"] = "new"  # Raises TypeError
        """
        return MappingProxyType(self._get_cached_data_dict())

    def get_data_as_dict(self) -> dict[str, SerializableValue]:
        """Convert the immutable data field to a dictionary for convenience.

        Returns a new dict copy each call to allow safe mutation by the caller.
        Internally caches the dict conversion for performance on repeated calls.

        Performance Note:
            The dict conversion is cached internally. Subsequent calls return
            a shallow copy of the cached dict, which is faster than rebuilding
            from the tuple each time. For read-only access without copying,
            use the data_as_dict property instead.

        Returns:
            dict[str, SerializableValue]: The data as a mutable dictionary (copy).

        Example:
            >>> payload = ModelReducerIntentPayload(data=(("key", "value"),))
            >>> payload.get_data_as_dict()
            {'key': 'value'}
        """
        return self._get_cached_data_dict().copy()

    def is_retryable(self) -> bool:
        """Check if this intent can be retried based on retry configuration.

        Returns:
            bool: True if retry_count < max_retries, False otherwise.

        Example:
            >>> payload = ModelReducerIntentPayload(retry_count=2, max_retries=5)
            >>> payload.is_retryable()
            True
            >>> payload = ModelReducerIntentPayload(retry_count=5, max_retries=5)
            >>> payload.is_retryable()
            False
        """
        return self.retry_count < self.max_retries

    def with_incremented_retry(self) -> "ModelReducerIntentPayload":
        """Create a new payload with incremented retry count.

        Since ModelReducerIntentPayload is frozen (immutable), this returns a new
        instance with retry_count incremented by 1.

        Returns:
            ModelReducerIntentPayload: New instance with retry_count += 1.

        Example:
            >>> payload = ModelReducerIntentPayload(retry_count=1)
            >>> new_payload = payload.with_incremented_retry()
            >>> new_payload.retry_count
            2
        """
        return self.model_copy(update={"retry_count": self.retry_count + 1})
