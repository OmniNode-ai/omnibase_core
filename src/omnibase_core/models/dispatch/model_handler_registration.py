"""
Handler Registration Model.

Represents metadata about a registered handler in the dispatch engine.
Handlers are the execution units that process messages after routing.

Design Pattern:
    ModelHandlerRegistration is a pure data model that captures handler metadata:
    - Handler identity (unique ID, human-readable name)
    - Handler capabilities (what message categories/types it can handle)
    - Handler configuration (timeout, concurrency limits)
    - Health and status information

    This model is used by the dispatch engine to:
    1. Register handlers during startup
    2. Validate that routes reference valid handlers
    3. Track handler health and availability
    4. Configure handler execution parameters

Thread Safety:
    ModelHandlerRegistration is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelHandlerRegistration
    >>> from omnibase_core.enums import EnumMessageCategory, EnumNodeKind
    >>>
    >>> # Register a handler for user events
    >>> handler = ModelHandlerRegistration(
    ...     handler_id="user-event-handler",
    ...     handler_name="User Event Handler",
    ...     node_kind=EnumNodeKind.REDUCER,
    ...     supported_categories=[EnumMessageCategory.EVENT],
    ...     timeout_seconds=30,
    ...     max_concurrent=10,
    ... )

See Also:
    omnibase_core.models.dispatch.ModelDispatchRoute: Uses handler_id to reference handlers
    omnibase_core.models.dispatch.ModelDispatchResult: Reports handler execution results
    omnibase_core.enums.EnumNodeKind: Node type classification
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind


class ModelHandlerRegistration(BaseModel):
    """
    Metadata about a registered handler in the dispatch engine.

    Captures all information needed to configure and manage a handler,
    including its capabilities, configuration, and health status.

    Attributes:
        handler_id: Unique identifier for this handler (referenced by routes).
        handler_name: Human-readable name for the handler.
        node_kind: The ONEX node kind this handler represents.
        node_id: Optional UUID of the node instance implementing this handler.
        supported_categories: Message categories this handler can process.
        supported_message_types: Specific message types this handler accepts.
            When empty, accepts all message types in supported categories.
        timeout_seconds: Maximum execution time before timeout.
        max_concurrent: Maximum concurrent executions allowed.
        max_retries: Maximum retry attempts for failed executions.
        enabled: Whether this handler is currently accepting messages.
        healthy: Whether this handler is currently healthy.
        last_health_check: Timestamp of the last health check.
        registered_at: Timestamp when this handler was registered.
        version: Handler version string for identification.
        description: Human-readable description of the handler's purpose.
        tags: Optional tags for categorization and filtering.
        metadata: Optional additional metadata about the handler.

    Example:
        >>> handler = ModelHandlerRegistration(
        ...     handler_id="order-processor",
        ...     handler_name="Order Processing Handler",
        ...     node_kind=EnumNodeKind.ORCHESTRATOR,
        ...     supported_categories=[EnumMessageCategory.COMMAND],
        ...     supported_message_types=["CreateOrderCommand", "CancelOrderCommand"],
        ...     timeout_seconds=60,
        ...     max_concurrent=5,
        ...     description="Processes order commands and coordinates fulfillment",
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Handler Identity ----
    handler_id: str = Field(
        ...,
        description="Unique identifier for this handler (referenced by routes).",
        min_length=1,
        max_length=200,
    )
    handler_name: str = Field(
        ...,
        description="Human-readable name for the handler.",
        min_length=1,
        max_length=200,
    )

    # ---- Node Information ----
    node_kind: EnumNodeKind = Field(
        ...,
        description="The ONEX node kind this handler represents.",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Optional UUID of the node instance implementing this handler.",
    )

    # ---- Capabilities ----
    supported_categories: list[EnumMessageCategory] = Field(
        ...,
        description="Message categories this handler can process.",
        min_length=1,
    )
    supported_message_types: list[str] = Field(
        default_factory=list,
        description=(
            "Specific message types this handler accepts. "
            "When empty, accepts all message types in supported categories."
        ),
    )

    # ---- Execution Configuration ----
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time before timeout.",
        ge=1,
        le=3600,
    )
    max_concurrent: int = Field(
        default=10,
        description="Maximum concurrent executions allowed.",
        ge=1,
        le=1000,
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed executions.",
        ge=0,
        le=10,
    )

    # ---- Status ----
    enabled: bool = Field(
        default=True,
        description="Whether this handler is currently accepting messages.",
    )
    healthy: bool = Field(
        default=True,
        description="Whether this handler is currently healthy.",
    )
    last_health_check: datetime | None = Field(
        default=None,
        description="Timestamp of the last health check (UTC).",
    )

    # ---- Registration Metadata ----
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this handler was registered (UTC).",
    )
    version: str | None = Field(
        default=None,
        description="Handler version string for identification.",
        max_length=50,
    )

    # ---- Documentation ----
    description: str | None = Field(
        default=None,
        description="Human-readable description of the handler's purpose.",
        max_length=1000,
    )

    # ---- Optional Metadata ----
    tags: list[str] | None = Field(
        default=None,
        description="Optional tags for categorization and filtering.",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional additional metadata about the handler.",
    )

    def supports_category(self, category: EnumMessageCategory) -> bool:
        """
        Check if this handler supports the given message category.

        Args:
            category: The message category to check

        Returns:
            True if the handler supports this category, False otherwise

        Example:
            >>> handler = ModelHandlerRegistration(
            ...     handler_id="test",
            ...     handler_name="Test Handler",
            ...     node_kind=EnumNodeKind.REDUCER,
            ...     supported_categories=[EnumMessageCategory.EVENT],
            ... )
            >>> handler.supports_category(EnumMessageCategory.EVENT)
            True
            >>> handler.supports_category(EnumMessageCategory.COMMAND)
            False
        """
        return category in self.supported_categories

    def supports_message_type(self, message_type: str) -> bool:
        """
        Check if this handler supports the given message type.

        If supported_message_types is empty, accepts all message types.

        Args:
            message_type: The message type to check

        Returns:
            True if the handler supports this message type, False otherwise

        Example:
            >>> handler = ModelHandlerRegistration(
            ...     handler_id="test",
            ...     handler_name="Test Handler",
            ...     node_kind=EnumNodeKind.REDUCER,
            ...     supported_categories=[EnumMessageCategory.EVENT],
            ...     supported_message_types=["UserCreated", "UserUpdated"],
            ... )
            >>> handler.supports_message_type("UserCreated")
            True
            >>> handler.supports_message_type("OrderCreated")
            False
        """
        if not self.supported_message_types:
            # Empty list means all message types are supported
            return True
        return message_type in self.supported_message_types

    def can_accept_message(
        self,
        category: EnumMessageCategory,
        message_type: str | None = None,
    ) -> bool:
        """
        Check if this handler can accept a message with the given category and type.

        Args:
            category: The message category
            message_type: Optional message type

        Returns:
            True if the handler can accept this message, False otherwise

        Example:
            >>> handler = ModelHandlerRegistration(
            ...     handler_id="test",
            ...     handler_name="Test Handler",
            ...     node_kind=EnumNodeKind.REDUCER,
            ...     supported_categories=[EnumMessageCategory.EVENT],
            ...     supported_message_types=["UserCreated"],
            ... )
            >>> handler.can_accept_message(EnumMessageCategory.EVENT, "UserCreated")
            True
            >>> handler.can_accept_message(EnumMessageCategory.EVENT, "OrderCreated")
            False
        """
        if not self.enabled:
            return False
        if not self.healthy:
            return False
        if not self.supports_category(category):
            return False
        if message_type is not None and not self.supports_message_type(message_type):
            return False
        return True

    def is_available(self) -> bool:
        """
        Check if this handler is available to accept messages.

        A handler is available if it is both enabled and healthy.

        Returns:
            True if the handler is available, False otherwise
        """
        return self.enabled and self.healthy

    def with_health_status(
        self,
        healthy: bool,
        check_time: datetime | None = None,
    ) -> "ModelHandlerRegistration":
        """
        Create a new registration with updated health status.

        Args:
            healthy: The new health status
            check_time: Optional timestamp for the health check (defaults to now)

        Returns:
            New ModelHandlerRegistration with updated health status
        """
        return self.model_copy(
            update={
                "healthy": healthy,
                "last_health_check": check_time or datetime.now(UTC),
            }
        )

    def with_enabled(self, enabled: bool) -> "ModelHandlerRegistration":
        """
        Create a new registration with updated enabled status.

        Args:
            enabled: The new enabled status

        Returns:
            New ModelHandlerRegistration with updated enabled status
        """
        return self.model_copy(update={"enabled": enabled})


__all__ = ["ModelHandlerRegistration"]
