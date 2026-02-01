"""
Mixin for contract-driven handler routing.

Enables nodes (Orchestrator, Effect) to route messages to handlers based on
YAML contract configuration rather than hardcoded logic. The routing is
deterministic: for a given (contract_version, routing_key) pair, the same
handlers are always returned.

Routing Strategies:
- payload_type_match: Route by event model class name (for orchestrators)
- operation_match: Route by operation field value (for effects)
- topic_pattern: Route by topic glob pattern matching (first-match-wins)

Example YAML contract:
    handler_routing:
      version: { major: 1, minor: 0, patch: 0 }
      routing_strategy: payload_type_match
      handlers:
        - routing_key: UserCreatedEvent
          handler_key: handle_user_created
          priority: 0
      default_handler: handle_unknown

Usage:
    class NodeMyOrchestrator(NodeOrchestrator, MixinHandlerRouting):
        def __init__(self, container: ModelONEXContainer, contract: ModelContract):
            super().__init__(container)
            # Initialize handler routing from contract
            # Use protocol-based DI token per ONEX conventions
            registry = container.get_service("ProtocolHandlerRegistry")
            self._init_handler_routing(
                contract.handler_routing,
                registry
            )

Typing: Strongly typed with strategic use of Protocol for handler resolution.

Performance Characteristics (topic_pattern strategy):
    - Patterns are pre-compiled to regex at initialization time (O(n) once)
    - Routing lookups use compiled regex matching (O(n) per lookup, n = patterns)
    - Routing results are cached per-instance (128 entries with FIFO eviction)
    - Expected scale: Optimized for 10-100 patterns; performs well up to 1000+
    - For very high-frequency routing (>10k/sec), consider payload_type_match
      which uses O(1) dict lookup instead of O(n) pattern matching.
"""

from __future__ import annotations

import fnmatch
import re
from re import Pattern
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
        ModelHandlerRoutingSubcontract,
    )
    from omnibase_core.protocols.runtime.protocol_handler_registry import (
        ProtocolHandlerRegistry,
    )
    from omnibase_core.protocols.runtime.protocol_message_handler import (
        ProtocolMessageHandler,
    )

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_handler_routing_strategy import EnumHandlerRoutingStrategy
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["MixinHandlerRouting"]

# Maximum size for per-instance topic pattern cache (FIFO eviction when exceeded)
_TOPIC_PATTERN_CACHE_MAX_SIZE = 128


class MixinHandlerRouting:
    """
    Mixin providing contract-driven handler routing for nodes.

    Enables orchestrator and effect nodes to route messages to appropriate
    handlers based on YAML contract configuration. The routing is deterministic:
    for a given (contract_version, routing_key) pair, the same handlers are
    always returned.

    Routing Strategies:
    - payload_type_match: Route by event/message model class name (orchestrators)
    - operation_match: Route by operation field value (effects)
    - topic_pattern: Route by topic glob pattern matching (first-match-wins:
      patterns are evaluated in routing table order, and the first matching
      pattern's handlers are returned; subsequent patterns are not evaluated)

    Thread Safety:
        WARNING: This mixin is NOT fully thread-safe for concurrent routing calls.

        The routing table (_handler_routing_table) and compiled patterns
        (_compiled_patterns) are read-only after initialization. However, the
        topic_pattern cache (_topic_pattern_cache) is MUTATED during
        route_to_handlers() calls for the topic_pattern strategy.

        Do NOT share node instances using this mixin across threads without
        external synchronization. Use separate node instances per thread.
        See docs/guides/THREADING.md for ONEX thread safety patterns.

        The registry must be frozen before use (enforced by route_to_handlers and
        validate_handler_routing methods).

    Usage:
        class NodeMyOrchestrator(NodeOrchestrator, MixinHandlerRouting):
            # Contract-driven routing - no custom routing code needed
            pass

    Attributes:
        _handler_routing_table: Mapping of routing_key to list of handler_keys.
        _handler_registry: Reference to the ProtocolHandlerRegistry for handler lookup.
        _routing_strategy: The routing strategy from the contract.
        _default_handler_key: Default handler key for unmatched routing keys.
        _routing_initialized: Whether routing has been initialized.
        _compiled_patterns: Pre-compiled regex patterns for topic_pattern strategy.
            List of (compiled_regex, handler_keys) tuples in evaluation order.
    """

    # Type annotations for mixin attributes
    _handler_routing_table: dict[str, list[str]]
    _handler_registry: ProtocolHandlerRegistry | None
    _routing_strategy: EnumHandlerRoutingStrategy
    _default_handler_key: str | None
    _routing_initialized: bool
    _compiled_patterns: list[tuple[Pattern[str], list[str]]]
    _topic_pattern_cache: dict[str, tuple[str, ...] | None]

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize handler routing mixin.

        Args:
            **kwargs: Passed to super().__init__() for cooperative MRO.
        """
        super().__init__(**kwargs)

        # Initialize routing state
        self._handler_routing_table = {}
        self._handler_registry = None
        self._routing_strategy = EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
        self._default_handler_key = None
        self._routing_initialized = False
        self._compiled_patterns = []
        self._topic_pattern_cache = {}

    def _init_handler_routing(
        self,
        handler_routing: ModelHandlerRoutingSubcontract | None,
        registry: ProtocolHandlerRegistry,
    ) -> None:
        """
        Initialize routing table from contract.

        Parses the handler_routing subcontract and builds an internal routing
        table for fast handler lookup. This method should be called during
        node initialization after the contract is loaded.

        Args:
            handler_routing: Handler routing subcontract from node contract.
                If None, routing will use default_handler only.
            registry: The ProtocolHandlerRegistry for handler resolution.
                Must be frozen before handler lookup is performed.

        Raises:
            ModelOnexError: If registry is None (INVALID_PARAMETER).

        Example:
            def __init__(self, container, contract):
                super().__init__(container)
                # Use protocol-based DI token per ONEX conventions
                registry = container.get_service("ProtocolHandlerRegistry")
                self._init_handler_routing(contract.handler_routing, registry)
        """
        if registry is None:
            raise ModelOnexError(
                message="ProtocolHandlerRegistry cannot be None for handler routing",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        self._handler_registry = registry

        if handler_routing is None:
            # No routing configuration - empty table, rely on default handler
            self._handler_routing_table = {}
            self._routing_strategy = EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
            self._default_handler_key = None
            self._compiled_patterns = []
            self._routing_initialized = True
            # Clear per-instance cache from previous initialization
            self._topic_pattern_cache = {}
            return

        # Build routing table from contract
        self._handler_routing_table = handler_routing.build_routing_table()
        self._routing_strategy = handler_routing.routing_strategy
        self._default_handler_key = handler_routing.default_handler

        # Pre-compile patterns for topic_pattern strategy (performance optimization)
        # This converts glob patterns to compiled regex at init time instead of
        # re-translating patterns on every routing call.
        self._compiled_patterns = []
        if self._routing_strategy == EnumHandlerRoutingStrategy.TOPIC_PATTERN:
            for pattern, handler_keys in self._handler_routing_table.items():
                # fnmatch.translate converts glob pattern to regex pattern
                regex_pattern = fnmatch.translate(pattern)
                compiled = re.compile(regex_pattern)
                self._compiled_patterns.append((compiled, handler_keys))

        # Clear per-instance cache from previous initialization
        self._topic_pattern_cache = {}
        self._routing_initialized = True

    def route_to_handlers(
        self,
        routing_key: str,
        category: EnumMessageCategory,
    ) -> list[ProtocolMessageHandler]:
        """
        Get handlers for the given routing key.

        Looks up handlers in the routing table based on the routing key and
        the configured routing strategy. Falls back to default_handler if
        no match is found.

        Args:
            routing_key: The routing key to look up. Interpretation depends
                on routing_strategy:
                - payload_type_match: Event model class name (e.g., "UserCreatedEvent")
                - operation_match: Operation field value (e.g., "create_user")
                - topic_pattern: Topic name for glob matching
            category: The message category for filtering handlers.

        Returns:
            list[ProtocolMessageHandler]: List of handlers for the routing key,
                filtered by category. Returns an empty list in these scenarios:

                1. **No routing key match and no default handler**: The routing_key
                   does not match any entry in the routing table, and no
                   default_handler is configured in the contract.

                2. **Handler not found in registry**: The handler_key from the
                   routing table or default_handler cannot be resolved via
                   ProtocolHandlerRegistry.get_handler_by_id(). This indicates
                   a misconfiguration between the contract and registered handlers.

                3. **Handler category mismatch**: All matched handlers have a
                   category that differs from the requested category parameter.
                   A DEBUG log is emitted for each filtered handler.

        Raises:
            ModelOnexError: If routing is not initialized (INVALID_STATE).
            ModelOnexError: If registry is not frozen (INVALID_STATE).

        Example:
            handlers = self.route_to_handlers(
                routing_key="UserCreatedEvent",
                category=EnumMessageCategory.EVENT
            )
            for handler in handlers:
                result = await handler.handle(envelope)
        """
        if not self._routing_initialized:
            raise ModelOnexError(
                message="Handler routing not initialized. Call _init_handler_routing() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        if self._handler_registry is None:
            raise ModelOnexError(
                message="ProtocolHandlerRegistry is None. Routing cannot proceed.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        # Enforce frozen contract for thread safety
        if not self._handler_registry.is_frozen:
            raise ModelOnexError(
                message="ProtocolHandlerRegistry is not frozen. "
                "Registration MUST complete and freeze() MUST be called before routing. "
                "This is required for thread safety.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        # Look up handler keys for the routing key
        handler_keys = self._get_handler_keys_for_routing_key(routing_key)

        # Resolve handler keys to handler instances
        handlers: list[ProtocolMessageHandler] = []
        for handler_key in handler_keys:
            handler = self._handler_registry.get_handler_by_id(handler_key)
            if handler is not None:
                # Filter by category if handler has category mismatch
                if handler.category == category:
                    handlers.append(handler)
                else:
                    emit_log_event(
                        LogLevel.DEBUG,
                        "Handler filtered due to category mismatch",
                        {
                            "handler_key": handler_key,
                            "expected_category": category.value,
                            "actual_category": handler.category.value,
                            "routing_key": routing_key,
                        },
                    )

        if not handlers:
            emit_log_event(
                LogLevel.DEBUG,
                "No handlers found for routing key",
                {
                    "routing_key": routing_key,
                    "category": category.value,
                    "routing_strategy": self._routing_strategy.value,
                    "has_default_handler": self._default_handler_key is not None,
                },
            )

        return handlers

    def _get_handler_keys_for_routing_key(self, routing_key: str) -> list[str]:
        """
        Get handler keys for a routing key based on routing strategy.

        Args:
            routing_key: The routing key to look up.

        Returns:
            list[str]: Copy of handler keys for the routing key.
                Returns a new list to prevent mutation of internal state.

        Note:
            For topic_pattern strategy, this method uses first-match-wins semantics:
            patterns are evaluated in iteration order, and the first matching
            pattern's handlers are returned. Subsequent patterns are NOT evaluated
            even if they would also match. This provides predictable, deterministic
            routing but requires careful pattern ordering in the contract.

        Performance:
            - payload_type_match/operation_match: O(1) dict lookup
            - topic_pattern: O(n) with pre-compiled regex, results cached (FIFO 128)
        """
        # Direct lookup for payload_type_match and operation_match
        if self._routing_strategy in (
            EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH,
            EnumHandlerRoutingStrategy.OPERATION_MATCH,
        ):
            handler_keys = self._handler_routing_table.get(routing_key)
            if handler_keys:
                # Return copy to prevent mutation of internal state
                return list(handler_keys)

        # Glob pattern matching for topic_pattern (uses compiled patterns + cache)
        elif self._routing_strategy == EnumHandlerRoutingStrategy.TOPIC_PATTERN:
            # Use cached lookup - returns tuple of handler keys or None
            cached_result = self._get_handler_keys_for_topic_pattern(routing_key)
            if cached_result is not None:
                # Return copy to prevent mutation of cached/internal state
                return list(cached_result)

        # Fall back to default handler
        if self._default_handler_key is not None:
            return [self._default_handler_key]

        return []

    def _get_handler_keys_for_topic_pattern(
        self, routing_key: str
    ) -> tuple[str, ...] | None:
        """
        Get handler keys for a routing key using pre-compiled topic patterns.

        Uses a per-instance cache to avoid repeated regex matching for
        frequently-used routing keys. This is thread-safe for read access
        after initialization (dict operations are atomic in CPython).

        Args:
            routing_key: The topic name to match against patterns.

        Returns:
            tuple[str, ...] | None: Tuple of handler keys if a pattern matches,
                None if no pattern matches. Returns tuple (immutable) for cache
                safety.

        Performance:
            - Cache hit: O(1)
            - Cache miss: O(n) where n = number of patterns
            - Cache size: 128 entries (FIFO eviction when exceeded)

        Note:
            This method uses first-match-wins semantics: patterns are evaluated
            in the order they appear in _compiled_patterns, and the first matching
            pattern's handlers are returned.

        Thread Safety:
            Uses per-instance cache instead of @lru_cache to avoid memory leaks
            and thread safety issues that arise from using @lru_cache on instance
            methods. The cache is safe for concurrent reads after initialization.
        """
        # Check per-instance cache first
        if routing_key in self._topic_pattern_cache:
            return self._topic_pattern_cache[routing_key]

        # Cache miss - compute result by matching against pre-compiled patterns
        result: tuple[str, ...] | None = None
        for compiled_regex, handler_keys in self._compiled_patterns:
            if compiled_regex.match(routing_key):
                # Return as tuple for cache immutability
                result = tuple(handler_keys)
                break

        # FIFO eviction if cache is full (simple bounded cache)
        # Note: This is NOT thread-safe for concurrent writes. In rare concurrent
        # scenarios, cache may temporarily exceed max size. This is acceptable per
        # ONEX thread safety policy (nodes are not shared across threads).
        # See docs/guides/THREADING.md for thread-local instance patterns.
        if len(self._topic_pattern_cache) >= _TOPIC_PATTERN_CACHE_MAX_SIZE:
            # Remove first (oldest) item - Python 3.7+ dicts maintain insertion order
            first_key = next(iter(self._topic_pattern_cache))
            del self._topic_pattern_cache[first_key]

        # Store result in cache (including None for no-match)
        self._topic_pattern_cache[routing_key] = result
        return result

    def validate_handler_routing(self) -> list[str]:
        """
        Validate all handlers in the routing table are resolvable.

        Checks that every handler_key referenced in the routing table
        and default_handler can be resolved from the ProtocolHandlerRegistry.

        Returns:
            list[str]: List of validation errors. Empty if all handlers valid.

        Raises:
            ModelOnexError: If routing is not initialized (INVALID_STATE).
            ModelOnexError: If registry is not frozen (INVALID_STATE).

        Example:
            errors = self.validate_handler_routing()
            if errors:
                for error in errors:
                    print(f"Validation error: {error}")
                raise ValueError("Handler routing validation failed")
        """
        if not self._routing_initialized:
            raise ModelOnexError(
                message="Handler routing not initialized. Call _init_handler_routing() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        if self._handler_registry is None:
            return ["ProtocolHandlerRegistry is None"]

        # Enforce frozen contract for thread safety
        if not self._handler_registry.is_frozen:
            raise ModelOnexError(
                message="ProtocolHandlerRegistry is not frozen. "
                "Registration MUST complete and freeze() MUST be called before validation. "
                "This is required for thread safety.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        errors: list[str] = []

        # Collect all handler keys from routing table
        all_handler_keys: set[str] = set()
        for handler_keys in self._handler_routing_table.values():
            all_handler_keys.update(handler_keys)

        if self._default_handler_key is not None:
            all_handler_keys.add(self._default_handler_key)

        # Validate each handler key is resolvable
        for handler_key in all_handler_keys:
            handler = self._handler_registry.get_handler_by_id(handler_key)
            if handler is None:
                errors.append(
                    f"Handler '{handler_key}' not found in ProtocolHandlerRegistry"
                )

        return errors

    def get_routing_table(self) -> dict[str, list[str]]:
        """
        Get a deep copy of the routing table for inspection.

        Returns:
            dict[str, list[str]]: Deep copy of the routing table mapping
                routing_key to list of handler_keys. Both the dict and
                the inner lists are new objects to prevent mutation of
                internal state.

        Raises:
            ModelOnexError: If routing is not initialized (INVALID_STATE).
        """
        if not self._routing_initialized:
            raise ModelOnexError(
                message="Handler routing not initialized. Call _init_handler_routing() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        # Deep copy: create new dict with new lists to prevent mutation
        return {k: list(v) for k, v in self._handler_routing_table.items()}

    @property
    def routing_strategy(self) -> EnumHandlerRoutingStrategy:
        """
        Get the configured routing strategy.

        Returns:
            EnumHandlerRoutingStrategy: The routing strategy.
        """
        return self._routing_strategy

    @property
    def default_handler_key(self) -> str | None:
        """
        Get the default handler key.

        Returns:
            str | None: The default handler key, or None if not configured.
        """
        return self._default_handler_key

    @property
    def is_routing_initialized(self) -> bool:
        """
        Check if handler routing has been initialized.

        Returns:
            bool: True if _init_handler_routing() has been called.
        """
        return self._routing_initialized
