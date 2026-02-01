"""
Dispatch Route Model.

Represents a routing rule that maps topic patterns and message types to handlers
in the runtime dispatch engine. Routes are used by the dispatcher to determine
which handler should process incoming messages.

Design Pattern:
    ModelDispatchRoute is a pure data model that defines a routing rule. It contains:
    - Topic pattern matching (exact or glob patterns)
    - Message category filtering (COMMAND, EVENT, INTENT)
    - Message type filtering (optional specific type within category)
    - Handler reference (identifier for the registered handler)
    - Priority for route ordering when multiple routes match

    The dispatch engine uses these routes to determine the appropriate handler
    for each incoming message based on topic and message type.

Thread Safety:
    ModelDispatchRoute is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelDispatchRoute
    >>> from omnibase_core.enums import EnumMessageCategory
    >>>
    >>> # Create a route for user events
    >>> route = ModelDispatchRoute(
    ...     route_id="user-events-route",
    ...     topic_pattern="*.user.events.*",
    ...     message_category=EnumMessageCategory.EVENT,
    ...     handler_id="user-event-handler",
    ...     priority=10,
    ... )
    >>>
    >>> # Check if route matches a topic
    >>> route.matches_topic("dev.user.events.v1")
    True

See Also:
    omnibase_core.models.dispatch.ModelHandlerRegistration: Handler metadata
    omnibase_core.models.dispatch.ModelDispatchResult: Dispatch operation result
    omnibase_core.enums.EnumMessageCategory: Message category enum
"""

import re
from functools import cached_property
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory


class ModelDispatchRoute(BaseModel):
    """
    Routing rule for the dispatch engine.

    Maps topic patterns and message types to handlers. Used by the dispatcher
    to determine which handler should process incoming messages.

    Attributes:
        route_id: Unique identifier for this route (for logging/debugging).
        topic_pattern: Topic pattern to match (exact string or glob pattern).
            Supports wildcards: '*' matches any single segment, '**' matches
            multiple segments.
        message_category: The message category this route handles (EVENT,
            COMMAND, or INTENT).
        message_type: Optional specific message type within the category.
            When None, matches all message types in the category.
        handler_id: Identifier of the handler to invoke when this route matches.
        priority: Route priority for ordering (higher = matched first).
            When multiple routes match, highest priority wins.
        enabled: Whether this route is active. Disabled routes are skipped.
        description: Human-readable description of the route's purpose.
        metadata: Optional additional metadata for the route.

    Example:
        >>> route = ModelDispatchRoute(
        ...     route_id="order-commands",
        ...     topic_pattern="*.order.commands.*",
        ...     message_category=EnumMessageCategory.COMMAND,
        ...     message_type="CreateOrderCommand",
        ...     handler_id="order-command-handler",
        ...     priority=100,
        ...     description="Routes order creation commands",
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Route Identity ----
    route_id: str = Field(
        ...,
        description="Unique identifier for this route (for logging/debugging).",
        min_length=1,
        max_length=200,
    )

    # ---- Matching Criteria ----
    topic_pattern: str = Field(
        ...,
        description=(
            "Topic pattern to match. Supports exact match or glob patterns. "
            "Use '*' for single segment wildcard, '**' for multi-segment."
        ),
        min_length=1,
        max_length=500,
    )
    message_category: EnumMessageCategory = Field(
        ...,
        description="The message category this route handles (EVENT, COMMAND, INTENT).",
    )
    message_type: str | None = Field(
        default=None,
        description=(
            "Optional specific message type within the category. "
            "When None, matches all message types in the category."
        ),
        max_length=200,
    )

    # ---- Handler Reference ----
    handler_id: str = Field(
        ...,
        description="Identifier of the handler to invoke when this route matches.",
        min_length=1,
        max_length=200,
    )

    # ---- Route Configuration ----
    priority: int = Field(
        default=0,
        description="Route priority for ordering. Higher priority routes are matched first.",
        ge=-1000,
        le=1000,
    )
    enabled: bool = Field(
        default=True,
        description="Whether this route is active. Disabled routes are skipped.",
    )

    # ---- Documentation ----
    description: str | None = Field(
        default=None,
        description="Human-readable description of the route's purpose.",
        max_length=1000,
    )

    # ---- Optional Metadata ----
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for tracing route creation.",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Optional additional metadata for the route.",
    )

    @field_validator("topic_pattern")
    @classmethod
    def validate_topic_pattern(cls, v: str) -> str:
        """Validate that the topic pattern is well-formed."""
        # Basic validation: must not be empty or only whitespace
        if not v or not v.strip():
            msg = "Topic pattern cannot be empty or whitespace"
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)
        # Pattern should not start/end with dots (invalid topic structure)
        if v.startswith(".") or v.endswith("."):
            msg = "Topic pattern cannot start or end with a dot"
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)
        return v

    @cached_property
    def _compiled_pattern(self) -> re.Pattern[str]:
        """
        Compile the topic pattern to a regex for efficient matching.

        Converts glob-style patterns to regex:
        - '*' matches any single segment (no dots)
        - '**' matches any number of segments (including dots)
        """
        # Escape special regex characters except * and **
        pattern = self.topic_pattern
        # Handle ** first (must be done before single *)
        pattern = pattern.replace("**", "__DOUBLE_STAR__")
        # Escape dots and other special chars
        pattern = re.escape(pattern)
        # Convert back ** placeholder to multi-segment match
        pattern = pattern.replace("__DOUBLE_STAR__", ".*")
        # Convert single * to single-segment match (no dots)
        pattern = pattern.replace(r"\*", "[^.]+")
        # Anchor the pattern
        return re.compile(f"^{pattern}$", re.IGNORECASE)

    def matches_topic(self, topic: str) -> bool:
        """
        Check if this route matches the given topic.

        Uses glob-style pattern matching where:
        - '*' matches any single segment (between dots)
        - '**' matches any number of segments

        Args:
            topic: The topic to check against this route's pattern

        Returns:
            True if the topic matches the pattern, False otherwise

        Example:
            >>> route = ModelDispatchRoute(
            ...     route_id="test",
            ...     topic_pattern="*.user.events.*",
            ...     message_category=EnumMessageCategory.EVENT,
            ...     handler_id="handler",
            ... )
            >>> route.matches_topic("dev.user.events.v1")
            True
            >>> route.matches_topic("user.commands.v1")
            False
        """
        if not self.enabled:
            return False
        return bool(self._compiled_pattern.match(topic))

    def matches(
        self,
        topic: str,
        category: EnumMessageCategory,
        message_type: str | None = None,
    ) -> bool:
        """
        Check if this route matches the given topic, category, and message type.

        A route matches if:
        1. The route is enabled
        2. The topic matches the pattern
        3. The category matches
        4. Either this route has no message_type filter, or the message types match

        Args:
            topic: The topic to check
            category: The message category to check
            message_type: Optional message type to check

        Returns:
            True if all criteria match, False otherwise

        Example:
            >>> route = ModelDispatchRoute(
            ...     route_id="test",
            ...     topic_pattern="*.user.events.*",
            ...     message_category=EnumMessageCategory.EVENT,
            ...     message_type="UserCreatedEvent",
            ...     handler_id="handler",
            ... )
            >>> route.matches("dev.user.events.v1", EnumMessageCategory.EVENT, "UserCreatedEvent")
            True
            >>> route.matches("dev.user.events.v1", EnumMessageCategory.COMMAND, "UserCreatedEvent")
            False
        """
        if not self.enabled:
            return False
        if not self.matches_topic(topic):
            return False
        if self.message_category != category:
            return False
        if self.message_type is not None and self.message_type != message_type:
            return False
        return True


__all__ = ["ModelDispatchRoute"]
