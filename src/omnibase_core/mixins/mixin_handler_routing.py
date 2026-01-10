# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Mixin for contract-driven handler routing.

Enables nodes (Orchestrator, Effect) to route messages to handlers based on
YAML contract configuration rather than hardcoded logic. The routing is
deterministic: for a given (contract_version, routing_key) pair, the same
handlers are always returned.

Routing Strategies:
- payload_type_match: Route by event model class name (for orchestrators)
- operation_match: Route by operation field value (for effects)
- topic_pattern: Route by topic glob pattern matching

Example YAML contract:
    handler_routing:
      version: { major: 1, minor: 0, patch: 0 }
      routing_strategy: payload_type_match
      handlers:
        - routing_key: UserCreatedEvent
          handler_id: handle_user_created
          priority: 0
      default_handler: handle_unknown

Usage:
    class NodeMyOrchestrator(NodeOrchestrator, MixinHandlerRouting):
        def __init__(self, container: ModelONEXContainer, contract: ModelContract):
            super().__init__(container)
            # Initialize handler routing from contract
            registry = container.get_service("ServiceHandlerRegistry")
            self._init_handler_routing(
                contract.handler_routing,
                registry
            )

Typing: Strongly typed with strategic use of Protocol for handler resolution.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
        ModelHandlerRoutingSubcontract,
    )
    from omnibase_core.protocols.runtime.protocol_message_handler import (
        ProtocolMessageHandler,
    )
    from omnibase_core.services.service_handler_registry import ServiceHandlerRegistry

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["MixinHandlerRouting"]


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
    - topic_pattern: Route by topic glob pattern matching

    Thread Safety:
        After initialization, the routing table is read-only and thread-safe.
        The registry must be frozen before use (enforced by ServiceHandlerRegistry).

    Usage:
        class NodeMyOrchestrator(NodeOrchestrator, MixinHandlerRouting):
            # Contract-driven routing - no custom routing code needed
            pass

    Attributes:
        _handler_routing_table: Mapping of routing_key to list of handler_keys.
        _handler_registry: Reference to the ServiceHandlerRegistry for handler lookup.
        _routing_strategy: The routing strategy from the contract.
        _default_handler_key: Default handler key for unmatched routing keys.
        _routing_initialized: Whether routing has been initialized.
    """

    # Type annotations for mixin attributes
    _handler_routing_table: dict[str, list[str]]
    _handler_registry: ServiceHandlerRegistry | None
    _routing_strategy: str
    _default_handler_key: str | None
    _routing_initialized: bool

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
        self._routing_strategy = "payload_type_match"
        self._default_handler_key = None
        self._routing_initialized = False

    def _init_handler_routing(
        self,
        handler_routing: ModelHandlerRoutingSubcontract | None,
        registry: ServiceHandlerRegistry,
    ) -> None:
        """
        Initialize routing table from contract.

        Parses the handler_routing subcontract and builds an internal routing
        table for fast handler lookup. This method should be called during
        node initialization after the contract is loaded.

        Args:
            handler_routing: Handler routing subcontract from node contract.
                If None, routing will use default_handler only.
            registry: The ServiceHandlerRegistry for handler resolution.
                Must be frozen before handler lookup is performed.

        Raises:
            ModelOnexError: If registry is None (INVALID_PARAMETER).

        Example:
            def __init__(self, container, contract):
                super().__init__(container)
                registry = container.get_service("ServiceHandlerRegistry")
                self._init_handler_routing(contract.handler_routing, registry)
        """
        if registry is None:
            raise ModelOnexError(
                message="ServiceHandlerRegistry cannot be None for handler routing",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        self._handler_registry = registry

        if handler_routing is None:
            # No routing configuration - empty table, rely on default handler
            self._handler_routing_table = {}
            self._routing_strategy = "payload_type_match"
            self._default_handler_key = None
            self._routing_initialized = True
            return

        # Build routing table from contract
        self._handler_routing_table = handler_routing.build_routing_table()
        self._routing_strategy = handler_routing.routing_strategy
        self._default_handler_key = handler_routing.default_handler
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
            list[ProtocolMessageHandler]: List of handlers for the routing key.
                Empty list if no handlers match and no default_handler is set.

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
                message="ServiceHandlerRegistry is None. Routing cannot proceed.",
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

        return handlers

    def _get_handler_keys_for_routing_key(self, routing_key: str) -> list[str]:
        """
        Get handler keys for a routing key based on routing strategy.

        Args:
            routing_key: The routing key to look up.

        Returns:
            list[str]: List of handler keys for the routing key.
        """
        # Direct lookup for payload_type_match and operation_match
        if self._routing_strategy in ("payload_type_match", "operation_match"):
            handler_keys = self._handler_routing_table.get(routing_key)
            if handler_keys:
                return handler_keys

        # Glob pattern matching for topic_pattern
        elif self._routing_strategy == "topic_pattern":
            for pattern, handler_keys in self._handler_routing_table.items():
                if fnmatch.fnmatch(routing_key, pattern):
                    return handler_keys

        # Fall back to default handler
        if self._default_handler_key is not None:
            return [self._default_handler_key]

        return []

    def validate_handler_routing(self) -> list[str]:
        """
        Validate all handlers in the routing table are resolvable.

        Checks that every handler_key referenced in the routing table
        and default_handler can be resolved from the ServiceHandlerRegistry.

        Returns:
            list[str]: List of validation errors. Empty if all handlers valid.

        Raises:
            ModelOnexError: If routing is not initialized (INVALID_STATE).

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
            return ["ServiceHandlerRegistry is None"]

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
                    f"Handler '{handler_key}' not found in ServiceHandlerRegistry"
                )

        return errors

    def get_routing_table(self) -> dict[str, list[str]]:
        """
        Get a copy of the routing table for inspection.

        Returns:
            dict[str, list[str]]: Copy of the routing table mapping
                routing_key to list of handler_keys.

        Raises:
            ModelOnexError: If routing is not initialized (INVALID_STATE).
        """
        if not self._routing_initialized:
            raise ModelOnexError(
                message="Handler routing not initialized. Call _init_handler_routing() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        return dict(self._handler_routing_table)

    @property
    def routing_strategy(self) -> str:
        """
        Get the configured routing strategy.

        Returns:
            str: The routing strategy (payload_type_match, operation_match, topic_pattern).
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
