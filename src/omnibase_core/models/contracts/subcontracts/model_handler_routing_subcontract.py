"""
Handler Routing Subcontract Model.

Pydantic model for contract-driven handler routing configuration.

This module provides the main subcontract model for defining how messages
are routed to handlers based on the ONEX contract `handler_routing` section.
These models enable MixinHandlerRouting to make routing decisions using
contract configuration rather than hardcoded logic.

Routing Strategies:
- payload_type_match: Route by event model class name (orchestrators)
- operation_match: Route by operation field value (effects)
- topic_pattern: Route by topic glob pattern matching (first-match-wins)

Example YAML contract configuration:
    handler_routing:
      version:
        major: 1
        minor: 0
        patch: 0
      routing_strategy: payload_type_match
      handlers:
        - routing_key: ModelEventJobCreated
          handler_key: handle_job_created
          message_category: event
          priority: 0
          output_events:
            - ModelEventJobStarted
        - routing_key: ModelEventJobCompleted
          handler_key: handle_job_completed
          priority: 10
      default_handler: handle_unknown

Key Invariant:
    Routing MUST be deterministic for a given (contract_version, routing_key) pair.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_routing_strategy import EnumHandlerRoutingStrategy
from omnibase_core.models.contracts.subcontracts.model_handler_routing_entry import (
    ModelHandlerRoutingEntry,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHandlerRoutingSubcontract(BaseModel):
    """
    Handler routing configuration subcontract.

    Defines contract-driven routing configuration for nodes that need to
    dispatch messages to specific handlers. This subcontract enables
    MixinHandlerRouting to make routing decisions based on YAML contract
    configuration rather than hardcoded logic.

    Routing Strategies:
    - payload_type_match: Route based on event payload model class name.
      Used by ORCHESTRATOR nodes to dispatch events to appropriate handlers.
    - operation_match: Route based on operation field in the message.
      Used by EFFECT nodes to dispatch to appropriate I/O handlers.
    - topic_pattern: Route based on glob pattern matching against topic.
      Used for topic-based subscription routing. Uses first-match-wins
      semantics: patterns are evaluated in priority order, and the first
      matching pattern's handlers are returned.

    Example YAML configuration:
        handler_routing:
          version:
            major: 1
            minor: 0
            patch: 0
          routing_strategy: payload_type_match
          handlers:
            - routing_key: ModelEventJobCreated
              handler_key: handle_job_created
              priority: 0
            - routing_key: ModelEventJobCompleted
              handler_key: handle_job_completed
              priority: 10
          default_handler: handle_unknown

    Example usage:
        >>> subcontract = ModelHandlerRoutingSubcontract(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     routing_strategy="payload_type_match",
        ...     handlers=[
        ...         ModelHandlerRoutingEntry(
        ...             routing_key="ModelEventJobCreated",
        ...             handler_key="handle_job_created"
        ...         )
        ...     ],
        ...     default_handler="handle_fallback"
        ... )
        >>> subcontract.routing_strategy.value
        'payload_type_match'
        >>> len(subcontract.handlers)
        1

    Strict typing is enforced: No Any types allowed in implementation.
    """

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    routing_strategy: EnumHandlerRoutingStrategy = Field(
        default=EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH,
        description="Strategy for routing events to handlers",
    )

    handlers: list[ModelHandlerRoutingEntry] = Field(
        default_factory=list,
        description=(
            "List of handler routing entries defining routing rules. "
            "Entries are evaluated in priority order (lower priority value first)"
        ),
    )

    default_handler: str | None = Field(
        default=None,
        description=(
            "Default handler registry key to use when no routing entries match. "
            "If None, unmatched messages may raise an error or be ignored "
            "depending on node implementation"
        ),
    )

    @model_validator(mode="after")
    def validate_routing_configuration(self) -> "ModelHandlerRoutingSubcontract":
        """Validate routing configuration after model construction.

        Validates:
        - No duplicate routing_keys (ensures deterministic routing)
        - At least one handler entry or default_handler is defined

        Raises:
            ModelOnexError: If validation fails (VALIDATION_ERROR).
                Per ADR-012, ModelOnexError is used in Pydantic validators
                for framework consistency and structured error context.
        """
        # Validate that configuration is not empty (at least one handler or default)
        if not self.handlers and self.default_handler is None:
            raise ModelOnexError(
                message="Empty routing configuration: must define at least one "
                "handler entry or a default_handler.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                # Standard context keys per ERROR_HANDLING_BEST_PRACTICES.md
                field="handlers",
                value=None,
                constraint="non_empty_configuration",
                # Domain-specific context
                routing_strategy=self.routing_strategy,
            )

        # Validate routing keys are unique (deterministic routing requirement)
        routing_keys: set[str] = set()
        for entry in self.handlers:
            if entry.routing_key in routing_keys:
                raise ModelOnexError(
                    message=f"Duplicate routing_key found: '{entry.routing_key}'. "
                    "Routing keys must be unique for deterministic routing.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    # Standard context keys per ERROR_HANDLING_BEST_PRACTICES.md
                    field="handlers.routing_key",
                    value=entry.routing_key,
                    constraint="unique_routing_key",
                    # Domain-specific context for debugging
                    handler_key=entry.handler_key,
                )
            routing_keys.add(entry.routing_key)

        return self

    def build_routing_table(self) -> dict[str, list[str]]:
        """
        Build a routing table mapping routing_key to handler_keys.

        The routing table is deterministic for a given (contract_version, routing_key)
        pair. Handler order is based on priority (lower priority value = first).

        Priority Ordering Behavior:
            Handlers are sorted by priority before building the routing table.
            Lower priority values are inserted first, which affects the iteration
            order of the resulting dictionary (Python 3.7+ preserves insertion order).

            This is significant for the ``topic_pattern`` routing strategy, which
            uses first-match-wins semantics: when iterating over the routing table
            to find a matching pattern, lower-priority entries are evaluated first.

            Example priority ordering:
                - priority=-10: Evaluated first (high-priority, specific patterns)
                - priority=0: Default priority (normal patterns)
                - priority=100: Evaluated last (catch-all/fallback patterns)

        Deterministic Routing:
            Duplicate routing_keys are prevented by model validation
            (``validate_routing_configuration``), ensuring each routing_key maps
            to exactly one handler. This guarantees deterministic routing for
            any given (contract_version, routing_key) pair.

        Returns:
            dict[str, list[str]]: Mapping of routing_key to list of handler_keys.
                The dictionary iteration order reflects priority ordering
                (lowest priority value first).

        Example:
            >>> subcontract = ModelHandlerRoutingSubcontract(
            ...     version=ModelSemVer(major=1, minor=0, patch=0),
            ...     handlers=[
            ...         ModelHandlerRoutingEntry(
            ...             routing_key="EventA",
            ...             handler_key="handler_a",
            ...             priority=0
            ...         ),
            ...         ModelHandlerRoutingEntry(
            ...             routing_key="EventB",
            ...             handler_key="handler_b",
            ...             priority=10
            ...         ),
            ...     ]
            ... )
            >>> routing_table = subcontract.build_routing_table()
            >>> routing_table
            {'EventA': ['handler_a'], 'EventB': ['handler_b']}

        Example with topic_pattern (first-match-wins):
            For topic_pattern strategy, priority determines evaluation order.
            A handler with routing_key="*.events.*" and priority=-10 will be
            checked before a handler with routing_key="*" and priority=100.
        """
        # Sort entries by priority (lower first = higher priority)
        sorted_entries = sorted(self.handlers, key=lambda e: e.priority)

        routing_table: dict[str, list[str]] = {}
        for entry in sorted_entries:
            if entry.routing_key not in routing_table:
                routing_table[entry.routing_key] = []
            routing_table[entry.routing_key].append(entry.handler_key)

        return routing_table

    def get_all_handler_keys(self) -> set[str]:
        """
        Get all unique handler keys referenced in this subcontract.

        Useful for validation to ensure all handlers are registered.

        Returns:
            set[str]: Set of all handler keys from routing entries and default handler.

        Example:
            >>> subcontract = ModelHandlerRoutingSubcontract(
            ...     version=ModelSemVer(major=1, minor=0, patch=0),
            ...     handlers=[
            ...         ModelHandlerRoutingEntry(
            ...             routing_key="EventA",
            ...             handler_key="handler_a"
            ...         ),
            ...     ],
            ...     default_handler="fallback"
            ... )
            >>> subcontract.get_all_handler_keys()
            {'handler_a', 'fallback'}
        """
        handler_keys: set[str] = {entry.handler_key for entry in self.handlers}
        if self.default_handler is not None:
            handler_keys.add(self.default_handler)
        return handler_keys
