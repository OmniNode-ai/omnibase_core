# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Comprehensive unit tests for MixinHandlerRouting.

Tests cover:
- Initialization with valid/empty/no handler routing configuration
- Routing strategies (payload_type_match, operation_match, topic_pattern)
- Handler resolution with and without default fallback
- Validation of handler routing configuration
- Determinism of routing for same (contract_version, routing_key)
- Node integration (NodeOrchestrator, NodeEffect, NodeCompute)

Related:
    - OMN-1293: MixinHandlerRouting for contract-driven handler routing
    - src/omnibase_core/mixins/mixin_handler_routing.py
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting
from omnibase_core.models.contracts.subcontracts.model_handler_routing_entry import (
    ModelHandlerRoutingEntry,
)
from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
    ModelHandlerRoutingSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Mock Classes
# =============================================================================


@runtime_checkable
class ProtocolMockHandler(Protocol):
    """Protocol defining the handler interface for type checking mocks.

    This protocol mirrors ProtocolMessageHandler for test mock typing.
    """

    @property
    def handler_id(self) -> str: ...

    @property
    def category(self) -> EnumMessageCategory: ...

    @property
    def message_types(self) -> set[str]: ...

    @property
    def node_kind(self) -> EnumNodeKind: ...

    async def handle(self, envelope: Any) -> Any: ...


class MockMessageHandler:
    """Mock handler implementing ProtocolMessageHandler for testing.

    This mock implements the same interface as ProtocolMessageHandler,
    providing the required properties and handle method for routing tests.

    See Also:
        omnibase_core.protocols.runtime.protocol_message_handler.ProtocolMessageHandler
    """

    def __init__(
        self,
        handler_id: str,
        category: EnumMessageCategory,
        node_kind: EnumNodeKind = EnumNodeKind.ORCHESTRATOR,
        message_types: set[str] | None = None,
    ) -> None:
        """Initialize mock handler with required properties.

        Args:
            handler_id: Unique identifier for the handler.
            category: Message category this handler processes.
            node_kind: Node kind for execution shape validation.
            message_types: Optional set of message types to handle.
        """
        self._handler_id: str = handler_id
        self._category: EnumMessageCategory = category
        self._node_kind: EnumNodeKind = node_kind
        self._message_types: set[str] = message_types or set()

    @property
    def handler_id(self) -> str:
        """Get the handler's unique identifier."""
        return self._handler_id

    @property
    def category(self) -> EnumMessageCategory:
        """Get the message category this handler processes."""
        return self._category

    @property
    def message_types(self) -> set[str]:
        """Get the set of message types this handler accepts."""
        return self._message_types

    @property
    def node_kind(self) -> EnumNodeKind:
        """Get the node kind for execution shape validation."""
        return self._node_kind

    async def handle(self, envelope: Any) -> dict[str, Any]:
        """Mock handle method.

        Args:
            envelope: The message envelope to process.

        Returns:
            dict with handler_id and processed flag.
        """
        return {"handler_id": self._handler_id, "processed": True}


class MockServiceHandlerRegistry:
    """Mock implementation of ServiceHandlerRegistry for testing handler routing.

    This mock follows the same interface contract as ServiceHandlerRegistry:
    - Handlers are registered by ID before freeze
    - Registry must be frozen before handler lookup
    - After freeze, no new handlers can be registered

    Follows the freeze-after-init pattern of the real ServiceHandlerRegistry.

    The mock provides the minimal interface needed by MixinHandlerRouting:
    - register_handler: Register handlers during setup
    - freeze: Lock registry for thread-safe read access
    - is_frozen: Check frozen state
    - get_handler_by_id: Look up handler by ID
    - handler_count: Get total registered handlers

    See Also:
        omnibase_core.services.service_handler_registry.ServiceHandlerRegistry
    """

    def __init__(self) -> None:
        """Initialize an empty, unfrozen handler registry."""
        self._handlers: dict[str, MockMessageHandler] = {}
        self._frozen: bool = False

    def register_handler(
        self,
        handler: MockMessageHandler,
        message_types: set[str] | None = None,
    ) -> None:
        """Register a handler by its ID.

        Args:
            handler: The handler to register (must have handler_id property).
            message_types: Optional message types (ignored in mock, mirrors real interface).

        Raises:
            ModelOnexError: If registry is already frozen.
        """
        if self._frozen:
            raise ModelOnexError(
                message="Registry is frozen",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        self._handlers[handler.handler_id] = handler

    def freeze(self) -> None:
        """Freeze the registry, preventing further handler registration."""
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        """Check if registry is frozen.

        Returns:
            True if registry is frozen and no more handlers can be registered.
        """
        return self._frozen

    @property
    def handler_count(self) -> int:
        """Get the total number of registered handlers.

        Returns:
            Number of handlers in the registry.
        """
        return len(self._handlers)

    def get_handler_by_id(self, handler_id: str) -> MockMessageHandler | None:
        """Get a handler by its ID.

        Args:
            handler_id: The unique identifier of the handler.

        Returns:
            The handler if found, None otherwise.
        """
        return self._handlers.get(handler_id)

    def get_handlers(
        self,
        category: EnumMessageCategory,
        message_type: str | None = None,
    ) -> list[MockMessageHandler]:
        """Get handlers matching the given category and optional message type.

        This method mirrors ProtocolHandlerRegistry.get_handlers to enable
        proper protocol compatibility for testing.

        Args:
            category: The message category to filter by.
            message_type: Optional specific message type to filter by.

        Returns:
            List of matching handlers, or empty list if none match.
        """
        matching: list[MockMessageHandler] = []
        for handler in self._handlers.values():
            if handler.category == category:
                if message_type is None or message_type in handler.message_types:
                    matching.append(handler)
        return matching


class TestNodeWithMixin(MixinHandlerRouting):
    """Test node class using MixinHandlerRouting."""

    def __init__(self) -> None:
        super().__init__()
        self.node_id = "test-node-001"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_registry() -> MockServiceHandlerRegistry:
    """Create a mock handler registry with some pre-registered handlers."""
    registry = MockServiceHandlerRegistry()

    # Register event handlers
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_user_created",
            category=EnumMessageCategory.EVENT,
            node_kind=EnumNodeKind.ORCHESTRATOR,
        )
    )
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_user_updated",
            category=EnumMessageCategory.EVENT,
            node_kind=EnumNodeKind.ORCHESTRATOR,
        )
    )
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_unknown",
            category=EnumMessageCategory.EVENT,
            node_kind=EnumNodeKind.ORCHESTRATOR,
        )
    )

    # Register command handlers
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_create_user",
            category=EnumMessageCategory.COMMAND,
            node_kind=EnumNodeKind.EFFECT,
        )
    )
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_http_get",
            category=EnumMessageCategory.COMMAND,
            node_kind=EnumNodeKind.EFFECT,
        )
    )

    registry.freeze()
    return registry


@pytest.fixture
def mock_registry_unfrozen() -> MockServiceHandlerRegistry:
    """Create an unfrozen mock handler registry for registration tests."""
    registry = MockServiceHandlerRegistry()
    registry.register_handler(
        MockMessageHandler(
            handler_id="handle_user_created",
            category=EnumMessageCategory.EVENT,
        )
    )
    return registry


@pytest.fixture
def sample_handler_routing() -> ModelHandlerRoutingSubcontract:
    """Create a sample handler routing subcontract with payload_type_match strategy."""
    return ModelHandlerRoutingSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        routing_strategy="payload_type_match",
        handlers=[
            ModelHandlerRoutingEntry(
                routing_key="UserCreatedEvent",
                handler_key="handle_user_created",
                priority=0,
            ),
            ModelHandlerRoutingEntry(
                routing_key="UserUpdatedEvent",
                handler_key="handle_user_updated",
                priority=10,
            ),
        ],
        default_handler="handle_unknown",
    )


@pytest.fixture
def operation_match_routing() -> ModelHandlerRoutingSubcontract:
    """Create a handler routing subcontract with operation_match strategy."""
    return ModelHandlerRoutingSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        routing_strategy="operation_match",
        handlers=[
            ModelHandlerRoutingEntry(
                routing_key="create_user",
                handler_key="handle_create_user",
                message_category=EnumMessageCategory.COMMAND,
                priority=0,
            ),
            ModelHandlerRoutingEntry(
                routing_key="http.get",
                handler_key="handle_http_get",
                priority=10,
            ),
        ],
        default_handler="handle_unknown",
    )


@pytest.fixture
def topic_pattern_routing() -> ModelHandlerRoutingSubcontract:
    """Create a handler routing subcontract with topic_pattern strategy."""
    return ModelHandlerRoutingSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        routing_strategy="topic_pattern",
        handlers=[
            ModelHandlerRoutingEntry(
                routing_key="events.user.*",
                handler_key="handle_user_created",
                priority=0,
            ),
            ModelHandlerRoutingEntry(
                routing_key="events.order.*",
                handler_key="handle_unknown",
                priority=10,
            ),
        ],
        default_handler="handle_unknown",
    )


@pytest.fixture
def empty_handlers_routing() -> ModelHandlerRoutingSubcontract:
    """Create a handler routing subcontract with empty handlers list."""
    return ModelHandlerRoutingSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        routing_strategy="payload_type_match",
        handlers=[],
        default_handler="handle_unknown",
    )


# =============================================================================
# Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestMixinHandlerRoutingInitialization:
    """Test MixinHandlerRouting initialization."""

    def test_init_handler_routing_with_valid_contract(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test routing table is built correctly from valid contract."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        assert node.is_routing_initialized is True
        assert node.routing_strategy == "payload_type_match"
        assert node.default_handler_key == "handle_unknown"

        # Verify routing table contents
        routing_table = node.get_routing_table()
        assert "UserCreatedEvent" in routing_table
        assert "UserUpdatedEvent" in routing_table
        assert routing_table["UserCreatedEvent"] == ["handle_user_created"]
        assert routing_table["UserUpdatedEvent"] == ["handle_user_updated"]

    def test_init_handler_routing_with_empty_handlers(
        self,
        mock_registry: MockServiceHandlerRegistry,
        empty_handlers_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test empty handlers list works and relies on default_handler."""
        node = TestNodeWithMixin()
        node._init_handler_routing(empty_handlers_routing, mock_registry)

        assert node.is_routing_initialized is True
        assert node.routing_strategy == "payload_type_match"
        assert node.default_handler_key == "handle_unknown"

        # Routing table should be empty
        routing_table = node.get_routing_table()
        assert routing_table == {}

    def test_init_handler_routing_without_contract(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test no error when handler_routing is None."""
        node = TestNodeWithMixin()
        node._init_handler_routing(None, mock_registry)

        assert node.is_routing_initialized is True
        assert node.routing_strategy == "payload_type_match"  # default
        assert node.default_handler_key is None

        # Routing table should be empty
        routing_table = node.get_routing_table()
        assert routing_table == {}

    def test_init_handler_routing_without_registry_raises_error(
        self,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that None registry raises ModelOnexError."""
        node = TestNodeWithMixin()

        with pytest.raises(ModelOnexError) as exc_info:
            node._init_handler_routing(sample_handler_routing, None)  # type: ignore[arg-type]

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER

    def test_mixin_initialization_defaults(self) -> None:
        """Test mixin initializes with correct default values."""
        node = TestNodeWithMixin()

        assert node._handler_routing_table == {}
        assert node._handler_registry is None
        assert node._routing_strategy == "payload_type_match"
        assert node._default_handler_key is None
        assert node._routing_initialized is False


# =============================================================================
# Routing Strategy Tests
# =============================================================================


@pytest.mark.unit
class TestRoutingStrategies:
    """Test different routing strategies."""

    def test_payload_type_match_strategy(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test routing by event model class name."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        # Route by payload type (event model class name)
        handlers = node.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_user_created"

    def test_operation_match_strategy(
        self,
        mock_registry: MockServiceHandlerRegistry,
        operation_match_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test routing by operation field value."""
        node = TestNodeWithMixin()
        node._init_handler_routing(operation_match_routing, mock_registry)

        # Verify strategy is operation_match
        assert node.routing_strategy == "operation_match"

        # Route by operation string
        handlers = node.route_to_handlers(
            routing_key="create_user",
            category=EnumMessageCategory.COMMAND,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_create_user"

    def test_topic_pattern_strategy(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test routing by glob pattern matching."""
        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Verify strategy is topic_pattern
        assert node.routing_strategy == "topic_pattern"

        # Route by topic pattern (glob match)
        handlers = node.route_to_handlers(
            routing_key="events.user.created",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_user_created"

        # Test a different topic that matches order pattern
        handlers = node.route_to_handlers(
            routing_key="events.order.completed",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_unknown"

    def test_topic_pattern_no_match_uses_default(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test topic pattern falls back to default when no pattern matches."""
        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Topic that doesn't match any pattern
        handlers = node.route_to_handlers(
            routing_key="events.inventory.updated",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_unknown"


# =============================================================================
# Handler Resolution Tests
# =============================================================================


@pytest.mark.unit
class TestHandlerResolution:
    """Test handler resolution."""

    def test_route_to_handlers_returns_correct_handlers(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that correct handlers are returned for routing key."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        handlers = node.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_user_created"
        assert handlers[0].category == EnumMessageCategory.EVENT

    def test_route_to_handlers_with_default_fallback(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test fallback to default_handler when no match found."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        # Use routing key that doesn't exist in handlers
        handlers = node.route_to_handlers(
            routing_key="UnknownEventType",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers) == 1
        assert handlers[0].handler_id == "handle_unknown"

    def test_route_to_handlers_with_no_match_no_default(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test returns empty list when no match and no default_handler."""
        # Create routing without default_handler
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="UserCreatedEvent",
                    handler_key="handle_user_created",
                ),
            ],
            default_handler=None,
        )

        node = TestNodeWithMixin()
        node._init_handler_routing(routing, mock_registry)

        # Use routing key that doesn't exist
        handlers = node.route_to_handlers(
            routing_key="UnknownEventType",
            category=EnumMessageCategory.EVENT,
        )

        assert handlers == []

    def test_route_to_handlers_filters_by_category(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that handlers are filtered by message category."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        # Handler exists but is registered for EVENT, not COMMAND
        handlers = node.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.COMMAND,
        )

        # Should return empty because handler category doesn't match
        assert handlers == []

    def test_route_to_handlers_before_init_raises_error(self) -> None:
        """Test that routing before initialization raises error."""
        node = TestNodeWithMixin()

        with pytest.raises(ModelOnexError) as exc_info:
            node.route_to_handlers(
                routing_key="UserCreatedEvent",
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_route_to_handlers_with_unfrozen_registry_raises_error(
        self,
        mock_registry_unfrozen: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that routing with unfrozen registry raises error."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry_unfrozen)

        with pytest.raises(ModelOnexError) as exc_info:
            node.route_to_handlers(
                routing_key="UserCreatedEvent",
                category=EnumMessageCategory.EVENT,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "not frozen" in str(exc_info.value).lower()

    def test_get_routing_table_before_init_raises_error(self) -> None:
        """Test that getting routing table before init raises error."""
        node = TestNodeWithMixin()

        with pytest.raises(ModelOnexError) as exc_info:
            node.get_routing_table()

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE


# =============================================================================
# Validation Tests
# =============================================================================


@pytest.mark.unit
class TestHandlerValidation:
    """Test handler routing validation."""

    def test_validate_handler_routing_all_resolvable(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test validation returns empty list when all handlers are valid."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        errors = node.validate_handler_routing()

        assert errors == []

    def test_validate_handler_routing_unresolvable_handler(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test validation returns errors for missing handlers."""
        # Create routing with non-existent handler
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="UserCreatedEvent",
                    handler_key="nonexistent_handler",
                ),
            ],
            default_handler=None,
        )

        node = TestNodeWithMixin()
        node._init_handler_routing(routing, mock_registry)

        errors = node.validate_handler_routing()

        assert len(errors) == 1
        assert "nonexistent_handler" in errors[0]
        assert "not found" in errors[0].lower()

    def test_validate_handler_routing_unresolvable_default(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test validation catches bad default_handler."""
        # Create routing with non-existent default handler
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="UserCreatedEvent",
                    handler_key="handle_user_created",
                ),
            ],
            default_handler="nonexistent_default",
        )

        node = TestNodeWithMixin()
        node._init_handler_routing(routing, mock_registry)

        errors = node.validate_handler_routing()

        assert len(errors) == 1
        assert "nonexistent_default" in errors[0]

    def test_validate_handler_routing_multiple_errors(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test validation returns all errors for multiple missing handlers."""
        # Create routing with multiple non-existent handlers
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="Event1",
                    handler_key="missing_handler_1",
                ),
                ModelHandlerRoutingEntry(
                    routing_key="Event2",
                    handler_key="missing_handler_2",
                ),
            ],
            default_handler="missing_default",
        )

        node = TestNodeWithMixin()
        node._init_handler_routing(routing, mock_registry)

        errors = node.validate_handler_routing()

        # Should have 3 errors: 2 handlers + 1 default
        assert len(errors) == 3

    def test_validate_handler_routing_before_init_raises_error(self) -> None:
        """Test validation before init raises error."""
        node = TestNodeWithMixin()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_handler_routing()

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_validate_handler_routing_with_none_registry(
        self,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test validation with None registry returns error."""
        node = TestNodeWithMixin()
        # Manually set routing initialized but no registry
        node._routing_initialized = True
        node._handler_registry = None
        node._handler_routing_table = {"UserCreatedEvent": ["handle_user_created"]}

        errors = node.validate_handler_routing()

        assert len(errors) == 1
        assert "None" in errors[0]

    def test_validate_handler_routing_with_unfrozen_registry_raises_error(
        self,
        mock_registry_unfrozen: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test validation raises error when registry is not frozen."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry_unfrozen)

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_handler_routing()

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "not frozen" in str(exc_info.value).lower()


# =============================================================================
# Determinism Tests
# =============================================================================


@pytest.mark.unit
class TestRoutingDeterminism:
    """Test deterministic routing behavior."""

    def test_routing_is_deterministic(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test same inputs always produce same routing."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        # Call route_to_handlers multiple times with same inputs
        results = []
        for _ in range(10):
            handlers = node.route_to_handlers(
                routing_key="UserCreatedEvent",
                category=EnumMessageCategory.EVENT,
            )
            results.append([h.handler_id for h in handlers])

        # All results should be identical
        assert all(r == results[0] for r in results)
        assert results[0] == ["handle_user_created"]

    def test_contract_change_updates_routing(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test different contract = different routing."""
        node = TestNodeWithMixin()

        # First contract version
        routing_v1 = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="UserCreatedEvent",
                    handler_key="handle_user_created",
                ),
            ],
            default_handler="handle_unknown",
        )

        node._init_handler_routing(routing_v1, mock_registry)
        handlers_v1 = node.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers_v1) == 1
        assert handlers_v1[0].handler_id == "handle_user_created"

        # Second contract version with different handler
        routing_v2 = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=2, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="UserCreatedEvent",
                    handler_key="handle_user_updated",  # Different handler
                ),
            ],
            default_handler="handle_unknown",
        )

        # Re-initialize with new contract
        node._routing_initialized = False  # Reset to allow re-init
        node._init_handler_routing(routing_v2, mock_registry)

        handlers_v2 = node.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.EVENT,
        )

        assert len(handlers_v2) == 1
        assert handlers_v2[0].handler_id == "handle_user_updated"

        # Results should be different
        assert handlers_v1[0].handler_id != handlers_v2[0].handler_id

    def test_routing_table_is_copy_not_reference(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test get_routing_table returns copy, not reference."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        table1 = node.get_routing_table()
        table2 = node.get_routing_table()

        # Should be equal but not same object
        assert table1 == table2
        assert table1 is not table2

        # Modifying copy should not affect internal state
        table1["NewKey"] = ["new_handler"]
        table3 = node.get_routing_table()
        assert "NewKey" not in table3


# =============================================================================
# Node Integration Tests
# =============================================================================


@pytest.mark.unit
class TestNodeIntegration:
    """Test integration with ONEX node classes."""

    def test_node_orchestrator_has_routing_capability(self) -> None:
        """Test NodeOrchestrator has MixinHandlerRouting methods."""
        from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

        # Verify class inherits from MixinHandlerRouting
        assert issubclass(NodeOrchestrator, MixinHandlerRouting)

        # Verify methods are available on class
        assert hasattr(NodeOrchestrator, "_init_handler_routing")
        assert hasattr(NodeOrchestrator, "route_to_handlers")
        assert hasattr(NodeOrchestrator, "validate_handler_routing")
        assert hasattr(NodeOrchestrator, "get_routing_table")
        assert hasattr(NodeOrchestrator, "routing_strategy")
        assert hasattr(NodeOrchestrator, "default_handler_key")
        assert hasattr(NodeOrchestrator, "is_routing_initialized")

    def test_node_effect_has_routing_capability(self) -> None:
        """Test NodeEffect has MixinHandlerRouting methods."""
        from omnibase_core.nodes.node_effect import NodeEffect

        # Verify class inherits from MixinHandlerRouting
        assert issubclass(NodeEffect, MixinHandlerRouting)

        # Verify methods are available on class
        assert hasattr(NodeEffect, "_init_handler_routing")
        assert hasattr(NodeEffect, "route_to_handlers")
        assert hasattr(NodeEffect, "validate_handler_routing")
        assert hasattr(NodeEffect, "get_routing_table")
        assert hasattr(NodeEffect, "routing_strategy")
        assert hasattr(NodeEffect, "default_handler_key")
        assert hasattr(NodeEffect, "is_routing_initialized")

    def test_node_compute_has_routing_capability(self) -> None:
        """Test NodeCompute has MixinHandlerRouting methods."""
        from omnibase_core.nodes.node_compute import NodeCompute

        # Verify class inherits from MixinHandlerRouting
        assert issubclass(NodeCompute, MixinHandlerRouting)

        # Verify methods are available on class
        assert hasattr(NodeCompute, "_init_handler_routing")
        assert hasattr(NodeCompute, "route_to_handlers")
        assert hasattr(NodeCompute, "validate_handler_routing")
        assert hasattr(NodeCompute, "get_routing_table")
        assert hasattr(NodeCompute, "routing_strategy")
        assert hasattr(NodeCompute, "default_handler_key")
        assert hasattr(NodeCompute, "is_routing_initialized")


# =============================================================================
# Edge Cases and Error Scenarios
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_multiple_handlers_same_routing_key_not_allowed(self) -> None:
        """Test that duplicate routing keys raise validation error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerRoutingSubcontract(
                version=ModelSemVer(major=1, minor=0, patch=0),
                routing_strategy="payload_type_match",
                handlers=[
                    ModelHandlerRoutingEntry(
                        routing_key="DuplicateKey",
                        handler_key="handler_1",
                    ),
                    ModelHandlerRoutingEntry(
                        routing_key="DuplicateKey",
                        handler_key="handler_2",
                    ),
                ],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "DuplicateKey" in str(exc_info.value)

    def test_empty_routing_key_not_allowed(self) -> None:
        """Test that empty routing_key raises validation error."""
        with pytest.raises(ValidationError):
            ModelHandlerRoutingEntry(
                routing_key="",
                handler_key="handler_1",
            )

    def test_empty_handler_key_not_allowed(self) -> None:
        """Test that empty handler_key raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelHandlerRoutingEntry(
                routing_key="ValidKey",
                handler_key="",
            )

    def test_handler_priority_ordering(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test handlers are ordered by priority when building routing table.

        The build_routing_table method should sort handlers by priority (ascending)
        before processing, ensuring lower priority values are processed first.
        This ordering is important for:
        1. Deterministic routing table construction
        2. First-match-wins behavior in topic_pattern strategy

        This test verifies:
        - Handlers with different priorities can be sorted correctly
        - The routing table is built with consistent ordering regardless of input order
        - Each routing_key maps to exactly one handler_key as expected
        """
        # Create handlers with different priorities in non-sorted order
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="EventA",
                    handler_key="handle_user_updated",
                    priority=10,  # Higher priority value (processed later)
                ),
                ModelHandlerRoutingEntry(
                    routing_key="EventB",
                    handler_key="handle_user_created",
                    priority=0,  # Lower priority value (processed first)
                ),
                ModelHandlerRoutingEntry(
                    routing_key="EventC",
                    handler_key="handle_unknown",
                    priority=5,  # Middle priority
                ),
            ],
        )

        # Verify handlers CAN BE sorted by priority (ascending = lower values first)
        sorted_handlers = sorted(routing.handlers, key=lambda h: h.priority)
        expected_order = [
            ("handle_user_created", 0),  # Lowest priority value = first
            ("handle_unknown", 5),  # Middle priority
            ("handle_user_updated", 10),  # Highest priority value = last
        ]
        for i, (expected_key, expected_priority) in enumerate(expected_order):
            assert sorted_handlers[i].handler_key == expected_key, (
                f"Position {i}: expected handler_key '{expected_key}', "
                f"got '{sorted_handlers[i].handler_key}'"
            )
            assert sorted_handlers[i].priority == expected_priority, (
                f"Position {i}: expected priority {expected_priority}, "
                f"got {sorted_handlers[i].priority}"
            )

        # Build routing table and verify deterministic output
        table = routing.build_routing_table()

        # Verify all routing_keys are present
        assert set(table.keys()) == {"EventA", "EventB", "EventC"}, (
            f"Expected routing keys {{'EventA', 'EventB', 'EventC'}}, got {set(table.keys())}"
        )

        # Verify each routing_key maps to exactly one handler_key
        assert table["EventA"] == ["handle_user_updated"], (
            f"EventA should map to ['handle_user_updated'], got {table['EventA']}"
        )
        assert table["EventB"] == ["handle_user_created"], (
            f"EventB should map to ['handle_user_created'], got {table['EventB']}"
        )
        assert table["EventC"] == ["handle_unknown"], (
            f"EventC should map to ['handle_unknown'], got {table['EventC']}"
        )

        # Verify determinism: building table twice gives same result
        table2 = routing.build_routing_table()
        assert table == table2, "Routing table should be deterministic across builds"

    def test_mixin_cooperative_inheritance(self) -> None:
        """Test mixin works with cooperative multiple inheritance."""

        class BaseClass:
            def __init__(self) -> None:
                self.base_initialized = True

        class TestNode(MixinHandlerRouting, BaseClass):
            def __init__(self) -> None:
                super().__init__()

        node = TestNode()

        # Both initializations should have run
        assert node.base_initialized is True
        assert node._routing_initialized is False

    def test_routing_with_handler_missing_from_registry(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test routing gracefully handles handler not in registry."""
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="MissingHandler",
                    handler_key="does_not_exist_in_registry",
                ),
            ],
            default_handler=None,
        )

        node = TestNodeWithMixin()
        node._init_handler_routing(routing, mock_registry)

        # route_to_handlers should return empty list for unresolvable handler
        handlers = node.route_to_handlers(
            routing_key="MissingHandler",
            category=EnumMessageCategory.EVENT,
        )

        assert handlers == []


# =============================================================================
# Property Tests
# =============================================================================


@pytest.mark.unit
class TestProperties:
    """Test property accessors."""

    def test_routing_strategy_property(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test routing_strategy property returns correct value."""
        node = TestNodeWithMixin()

        # Default before init
        assert node.routing_strategy == "payload_type_match"

        # After init with operation_match
        # Note: Empty handlers requires a default_handler per validation rules
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="operation_match",
            handlers=[],
            default_handler="fallback_handler",
        )
        node._init_handler_routing(routing, mock_registry)

        assert node.routing_strategy == "operation_match"

    def test_default_handler_key_property(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test default_handler_key property returns correct value."""
        node = TestNodeWithMixin()

        # Default before init
        assert node.default_handler_key is None

        # After init with default handler
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[],
            default_handler="my_default_handler",
        )
        node._init_handler_routing(routing, mock_registry)

        assert node.default_handler_key == "my_default_handler"

    def test_is_routing_initialized_property(
        self,
        mock_registry: MockServiceHandlerRegistry,
    ) -> None:
        """Test is_routing_initialized property returns correct value."""
        node = TestNodeWithMixin()

        # Before init
        assert node.is_routing_initialized is False

        # After init
        # Note: Empty handlers requires a default_handler per validation rules
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",
            handlers=[],
            default_handler="fallback_handler",
        )
        node._init_handler_routing(routing, mock_registry)

        assert node.is_routing_initialized is True


# =============================================================================
# Performance Optimization Tests
# =============================================================================


@pytest.mark.unit
class TestTopicPatternPerformanceOptimization:
    """Test topic_pattern performance optimizations.

    Verifies that:
    - Patterns are pre-compiled to regex at initialization time
    - Routing results are cached per-instance (FIFO eviction, thread-safe)
    - Cache is properly cleared on re-initialization
    """

    def test_patterns_are_precompiled_at_initialization(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that glob patterns are pre-compiled to regex at init time."""
        import re

        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Verify _compiled_patterns contains compiled regex objects
        assert len(node._compiled_patterns) == 2
        for compiled_regex, handler_keys in node._compiled_patterns:
            # Each entry should be (Pattern, list[str])
            assert isinstance(compiled_regex, re.Pattern)
            assert isinstance(handler_keys, list)
            assert all(isinstance(k, str) for k in handler_keys)

    def test_routing_cache_is_populated(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that routing results are cached after first lookup.

        Uses per-instance _topic_pattern_cache dict for caching.
        """
        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Per-instance cache should be empty initially
        assert len(node._topic_pattern_cache) == 0

        # First lookup - should populate cache
        node.route_to_handlers("events.user.created", EnumMessageCategory.EVENT)
        assert len(node._topic_pattern_cache) == 1
        assert "events.user.created" in node._topic_pattern_cache

        # Second lookup with same key - should use cached result
        node.route_to_handlers("events.user.created", EnumMessageCategory.EVENT)
        # Cache size should still be 1 (hit, not miss)
        assert len(node._topic_pattern_cache) == 1

        # Third lookup with different key - should add to cache
        node.route_to_handlers("events.order.completed", EnumMessageCategory.EVENT)
        assert len(node._topic_pattern_cache) == 2
        assert "events.order.completed" in node._topic_pattern_cache

    def test_cache_cleared_on_reinitialization(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that cache is cleared when routing is re-initialized.

        Uses per-instance _topic_pattern_cache dict which is cleared
        during re-initialization.
        """
        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Populate cache
        node.route_to_handlers("events.user.created", EnumMessageCategory.EVENT)
        node.route_to_handlers("events.user.updated", EnumMessageCategory.EVENT)
        assert len(node._topic_pattern_cache) > 0

        # Re-initialize with same routing
        node._routing_initialized = False  # Allow re-init
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Cache should be cleared
        assert len(node._topic_pattern_cache) == 0

    def test_no_compiled_patterns_for_non_topic_strategy(
        self,
        mock_registry: MockServiceHandlerRegistry,
        sample_handler_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that _compiled_patterns is empty for non-topic_pattern strategies."""
        node = TestNodeWithMixin()
        node._init_handler_routing(sample_handler_routing, mock_registry)

        # payload_type_match strategy should not compile patterns
        assert node.routing_strategy == "payload_type_match"
        assert len(node._compiled_patterns) == 0

    def test_cached_result_is_not_mutable(
        self,
        mock_registry: MockServiceHandlerRegistry,
        topic_pattern_routing: ModelHandlerRoutingSubcontract,
    ) -> None:
        """Test that modifying returned handler list doesn't affect cache."""
        node = TestNodeWithMixin()
        node._init_handler_routing(topic_pattern_routing, mock_registry)

        # Get handler keys (returns a copy)
        keys1 = node._get_handler_keys_for_routing_key("events.user.created")

        # Modify the returned list
        original_len = len(keys1)
        keys1.append("mutated_handler")

        # Get again - should not include our mutation
        keys2 = node._get_handler_keys_for_routing_key("events.user.created")
        assert len(keys2) == original_len
        assert "mutated_handler" not in keys2
