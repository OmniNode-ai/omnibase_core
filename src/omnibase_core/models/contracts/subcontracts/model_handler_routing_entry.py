"""
Handler Routing Entry Model.

NOTE: This module uses `from __future__ import annotations` for consistency
with model_handler_routing_subcontract.py and to enable forward references.

Pydantic model for a single handler routing entry in contract-driven
handler routing configuration.

Example YAML:
    - routing_key: ModelEventJobCreated
      handler_key: handle_job_created
      message_category: event
      priority: 0
      output_events:
        - ModelEventJobStarted

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory


class ModelHandlerRoutingEntry(BaseModel):
    """
    Single handler routing entry for contract-driven message routing.

    Each entry defines a mapping from a routing key to a handler identifier,
    with optional metadata for message categorization and priority ordering.

    The routing_key interpretation depends on the parent subcontract's
    routing_strategy:
    - payload_type_match: routing_key is the event model class name
      (e.g., "ModelEventJobCreated")
    - operation_match: routing_key is the operation string
      (e.g., "create_user", "http.get")
    - topic_pattern: routing_key is a glob pattern for topic matching
      (e.g., "*.events.*", "dev.user.commands.*")

    Example:
        >>> entry = ModelHandlerRoutingEntry(
        ...     routing_key="ModelEventJobCreated",
        ...     handler_key="handle_job_created",
        ...     message_category=EnumMessageCategory.EVENT,
        ...     priority=0,
        ...     output_events=["ModelEventJobStarted"]
        ... )
        >>> entry.routing_key
        'ModelEventJobCreated'
        >>> entry.handler_key
        'handle_job_created'

    Strict typing is enforced: No Any types allowed in implementation.
    """

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    routing_key: str = Field(
        ...,  # Required
        description=(
            "The key used for routing decisions. Interpretation depends on "
            "routing_strategy: event model name (payload_type_match), "
            "operation string (operation_match), or topic pattern (topic_pattern)"
        ),
        min_length=1,
    )

    handler_key: str = Field(
        ...,  # Required
        description=(
            "Handler registry key for lookup. Must match a registered "
            "handler method name or handler registry key"
        ),
        min_length=1,
    )

    message_category: EnumMessageCategory | None = Field(
        default=None,
        description=(
            "Optional message category (EVENT, COMMAND, INTENT) for filtering. "
            "If specified, only messages matching this category are routed "
            "to this handler"
        ),
    )

    priority: int = Field(
        default=0,
        ge=-1000,
        le=1000,
        description=(
            "Handler priority for ordering when multiple handlers match. "
            "Lower values = higher priority (evaluated first in routing table). "
            "Range: -1000 to 1000. Default 0 for normal priority. "
            "For topic_pattern strategy with first-match-wins semantics: "
            "use negative values (e.g., -100) for patterns that must match first "
            "(specific patterns), use positive values (e.g., 100) for fallback "
            "or catch-all patterns (e.g., '*' wildcard)"
        ),
    )

    output_events: list[str] = Field(
        default_factory=list,
        description=(
            "List of event model class names that this handler may emit. "
            "Used for documentation, validation, and graph analysis"
        ),
    )

    @field_validator("routing_key", "handler_key", mode="before")
    @classmethod
    def strip_and_validate_whitespace(cls, v: Any) -> Any:
        """
        Strip whitespace and reject empty/whitespace-only values.

        This prevents contract typos where keys contain leading/trailing
        whitespace or are entirely whitespace.

        Uses Any type hints because mode="before" validators receive
        raw input values before type coercion.
        """
        if not isinstance(v, str):
            return v  # Let Pydantic handle type validation
        stripped = v.strip()
        if not stripped:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError("Value cannot be empty or whitespace-only")
        return stripped
