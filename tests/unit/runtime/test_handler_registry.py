# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Unit tests for ServiceHandlerRegistry.

Tests the handler registry functionality including:
- Handler registration and validation
- Execution shape validation at registration time
- Freeze pattern behavior
- Handler lookup by category and message type
- Thread safety contract enforcement

Related:
    - OMN-934: Handler registry for message dispatch engine
    - src/omnibase_core/runtime/handler_registry.py
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.handler_registry import (
    ProtocolMessageHandler,
    ServiceHandlerRegistry,
)


class MockMessageHandler:
    """Mock handler implementing ProtocolMessageHandler for testing."""

    def __init__(
        self,
        handler_id: str,
        category: EnumMessageCategory,
        node_kind: EnumNodeKind,
        message_types: set[str] | None = None,
    ) -> None:
        self._handler_id = handler_id
        self._category = category
        self._node_kind = node_kind
        self._message_types = message_types or set()

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def category(self) -> EnumMessageCategory:
        return self._category

    @property
    def message_types(self) -> set[str]:
        return self._message_types

    @property
    def node_kind(self) -> EnumNodeKind:
        return self._node_kind

    async def handle(self, envelope: Any) -> ModelDispatchResult:
        return ModelDispatchResult(
            status=EnumDispatchStatus.SUCCESS,
            topic="test.events",
            handler_id=self._handler_id,
        )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def handler_registry() -> ServiceHandlerRegistry:
    """Create a fresh ServiceHandlerRegistry for tests."""
    return ServiceHandlerRegistry()


@pytest.fixture
def event_reducer_handler() -> MockMessageHandler:
    """Create a handler for EVENT -> REDUCER (valid shape)."""
    return MockMessageHandler(
        handler_id="event-reducer-handler",
        category=EnumMessageCategory.EVENT,
        node_kind=EnumNodeKind.REDUCER,
        message_types={"UserCreated", "UserUpdated"},
    )


@pytest.fixture
def event_orchestrator_handler() -> MockMessageHandler:
    """Create a handler for EVENT -> ORCHESTRATOR (valid shape)."""
    return MockMessageHandler(
        handler_id="event-orchestrator-handler",
        category=EnumMessageCategory.EVENT,
        node_kind=EnumNodeKind.ORCHESTRATOR,
    )


@pytest.fixture
def command_orchestrator_handler() -> MockMessageHandler:
    """Create a handler for COMMAND -> ORCHESTRATOR (valid shape)."""
    return MockMessageHandler(
        handler_id="command-orchestrator-handler",
        category=EnumMessageCategory.COMMAND,
        node_kind=EnumNodeKind.ORCHESTRATOR,
        message_types={"CreateOrder", "CancelOrder"},
    )


@pytest.fixture
def command_effect_handler() -> MockMessageHandler:
    """Create a handler for COMMAND -> EFFECT (valid shape)."""
    return MockMessageHandler(
        handler_id="command-effect-handler",
        category=EnumMessageCategory.COMMAND,
        node_kind=EnumNodeKind.EFFECT,
    )


@pytest.fixture
def intent_effect_handler() -> MockMessageHandler:
    """Create a handler for INTENT -> EFFECT (valid shape)."""
    return MockMessageHandler(
        handler_id="intent-effect-handler",
        category=EnumMessageCategory.INTENT,
        node_kind=EnumNodeKind.EFFECT,
        message_types={"SendEmail", "NotifyUser"},
    )


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolMessageHandler:
    """Tests for ProtocolMessageHandler protocol."""

    def test_mock_handler_implements_protocol(
        self, event_reducer_handler: MockMessageHandler
    ) -> None:
        """MockMessageHandler should implement ProtocolMessageHandler."""
        assert isinstance(event_reducer_handler, ProtocolMessageHandler)

    def test_handler_has_required_properties(
        self, event_reducer_handler: MockMessageHandler
    ) -> None:
        """Handler should have all required properties."""
        assert event_reducer_handler.handler_id == "event-reducer-handler"
        assert event_reducer_handler.category == EnumMessageCategory.EVENT
        assert event_reducer_handler.node_kind == EnumNodeKind.REDUCER
        assert event_reducer_handler.message_types == {"UserCreated", "UserUpdated"}

    @pytest.mark.asyncio
    async def test_handler_handle_method(
        self, event_reducer_handler: MockMessageHandler
    ) -> None:
        """Handler should have async handle method that returns ModelDispatchResult."""
        result = await event_reducer_handler.handle(MagicMock())
        assert isinstance(result, ModelDispatchResult)
        assert result.status == EnumDispatchStatus.SUCCESS


# =============================================================================
# Registration Tests
# =============================================================================


@pytest.mark.unit
class TestHandlerRegistration:
    """Tests for handler registration."""

    def test_register_valid_handler(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should register a valid handler successfully."""
        handler_registry.register_handler(event_reducer_handler)
        assert handler_registry.handler_count == 1

    def test_register_multiple_handlers(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
        event_orchestrator_handler: MockMessageHandler,
        command_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """Should register multiple handlers successfully."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.register_handler(event_orchestrator_handler)
        handler_registry.register_handler(command_orchestrator_handler)
        assert handler_registry.handler_count == 3

    def test_register_with_custom_message_types(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should allow overriding message_types at registration."""
        custom_types = {"CustomEvent1", "CustomEvent2"}
        handler_registry.register_handler(
            event_reducer_handler,
            message_types=custom_types,
        )
        handler_registry.freeze()

        # Should find handler with custom types
        handlers = handler_registry.get_handlers(
            EnumMessageCategory.EVENT,
            message_type="CustomEvent1",
        )
        assert len(handlers) == 1

        # Should NOT find with original types
        handlers = handler_registry.get_handlers(
            EnumMessageCategory.EVENT,
            message_type="UserCreated",
        )
        assert len(handlers) == 0

    def test_register_none_handler_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Should raise when registering None handler."""
        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(None)  # type: ignore[arg-type]

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        assert "None" in str(exc_info.value)

    def test_register_duplicate_handler_id_raises(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should raise when registering duplicate handler_id."""
        handler_registry.register_handler(event_reducer_handler)

        # Create another handler with same ID
        duplicate = MockMessageHandler(
            handler_id="event-reducer-handler",  # Same ID
            category=EnumMessageCategory.EVENT,
            node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(duplicate)

        assert exc_info.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION

    def test_register_handler_missing_handler_id_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Should raise when handler lacks handler_id property."""
        handler = MagicMock(spec=[])  # No handler_id attribute

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        assert "handler_id" in str(exc_info.value)

    def test_register_handler_missing_category_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Should raise when handler lacks category property."""
        handler = MagicMock()
        handler.handler_id = "test-handler"
        del handler.category

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        assert "category" in str(exc_info.value)


# =============================================================================
# Execution Shape Validation Tests
# =============================================================================


@pytest.mark.unit
class TestExecutionShapeValidation:
    """Tests for execution shape validation at registration time."""

    def test_valid_shapes_event_to_reducer(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """EVENT -> REDUCER is a valid execution shape."""
        handler_registry.register_handler(event_reducer_handler)
        assert handler_registry.handler_count == 1

    def test_valid_shapes_event_to_orchestrator(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """EVENT -> ORCHESTRATOR is a valid execution shape."""
        handler_registry.register_handler(event_orchestrator_handler)
        assert handler_registry.handler_count == 1

    def test_valid_shapes_command_to_orchestrator(
        self,
        handler_registry: ServiceHandlerRegistry,
        command_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """COMMAND -> ORCHESTRATOR is a valid execution shape."""
        handler_registry.register_handler(command_orchestrator_handler)
        assert handler_registry.handler_count == 1

    def test_valid_shapes_command_to_effect(
        self,
        handler_registry: ServiceHandlerRegistry,
        command_effect_handler: MockMessageHandler,
    ) -> None:
        """COMMAND -> EFFECT is a valid execution shape."""
        handler_registry.register_handler(command_effect_handler)
        assert handler_registry.handler_count == 1

    def test_valid_shapes_intent_to_effect(
        self,
        handler_registry: ServiceHandlerRegistry,
        intent_effect_handler: MockMessageHandler,
    ) -> None:
        """INTENT -> EFFECT is a valid execution shape."""
        handler_registry.register_handler(intent_effect_handler)
        assert handler_registry.handler_count == 1

    def test_invalid_shape_command_to_reducer_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """COMMAND -> REDUCER is an invalid execution shape."""
        invalid_handler = MockMessageHandler(
            handler_id="invalid-handler",
            category=EnumMessageCategory.COMMAND,
            node_kind=EnumNodeKind.REDUCER,  # Invalid!
        )

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(invalid_handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "invalid execution shape" in str(exc_info.value).lower()

    def test_invalid_shape_intent_to_reducer_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """INTENT -> REDUCER is an invalid execution shape."""
        invalid_handler = MockMessageHandler(
            handler_id="invalid-handler",
            category=EnumMessageCategory.INTENT,
            node_kind=EnumNodeKind.REDUCER,  # Invalid!
        )

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(invalid_handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_invalid_shape_event_to_effect_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """EVENT -> EFFECT is an invalid execution shape."""
        invalid_handler = MockMessageHandler(
            handler_id="invalid-handler",
            category=EnumMessageCategory.EVENT,
            node_kind=EnumNodeKind.EFFECT,  # Invalid!
        )

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(invalid_handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_invalid_shape_intent_to_orchestrator_raises(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """INTENT -> ORCHESTRATOR is an invalid execution shape."""
        invalid_handler = MockMessageHandler(
            handler_id="invalid-handler",
            category=EnumMessageCategory.INTENT,
            node_kind=EnumNodeKind.ORCHESTRATOR,  # Invalid!
        )

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(invalid_handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED


# =============================================================================
# Freeze Pattern Tests
# =============================================================================


@pytest.mark.unit
class TestFreezePattern:
    """Tests for freeze-after-init pattern."""

    def test_initial_state_not_frozen(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Registry should start unfrozen."""
        assert handler_registry.is_frozen is False

    def test_freeze_sets_frozen_flag(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """freeze() should set is_frozen to True."""
        handler_registry.freeze()
        assert handler_registry.is_frozen is True

    def test_freeze_is_idempotent(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Calling freeze() multiple times should be safe."""
        handler_registry.freeze()
        handler_registry.freeze()  # Should not raise
        handler_registry.freeze()  # Should not raise
        assert handler_registry.is_frozen is True

    def test_register_after_freeze_raises(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should raise when registering after freeze."""
        handler_registry.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.register_handler(event_reducer_handler)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "frozen" in str(exc_info.value).lower()

    def test_unregister_after_freeze_raises(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should raise when unregistering after freeze."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.unregister_handler("event-reducer-handler")

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

    def test_get_handlers_before_freeze_raises(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should raise when getting handlers before freeze."""
        handler_registry.register_handler(event_reducer_handler)

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.get_handlers(EnumMessageCategory.EVENT)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "freeze" in str(exc_info.value).lower()

    def test_get_handler_by_id_before_freeze_raises(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should raise when getting handler by ID before freeze."""
        handler_registry.register_handler(event_reducer_handler)

        with pytest.raises(ModelOnexError) as exc_info:
            handler_registry.get_handler_by_id("event-reducer-handler")

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE


# =============================================================================
# Handler Lookup Tests
# =============================================================================


@pytest.mark.unit
class TestHandlerLookup:
    """Tests for handler lookup after freeze."""

    def test_get_handlers_by_category(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
        event_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """Should return all handlers for a category."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.register_handler(event_orchestrator_handler)
        handler_registry.freeze()

        handlers = handler_registry.get_handlers(EnumMessageCategory.EVENT)
        assert len(handlers) == 2

    def test_get_handlers_by_category_and_type(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
        event_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """Should filter handlers by message type."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.register_handler(event_orchestrator_handler)
        handler_registry.freeze()

        # event_reducer_handler has specific types, event_orchestrator has none (all)
        handlers = handler_registry.get_handlers(
            EnumMessageCategory.EVENT,
            message_type="UserCreated",
        )
        # Both should match: reducer has UserCreated, orchestrator accepts all
        assert len(handlers) == 2

        # Only orchestrator should match (reducer doesn't have UnknownEvent)
        handlers = handler_registry.get_handlers(
            EnumMessageCategory.EVENT,
            message_type="UnknownEvent",
        )
        assert len(handlers) == 1
        assert handlers[0].handler_id == "event-orchestrator-handler"

    def test_get_handlers_empty_category(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should return empty list for category with no handlers."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.freeze()

        handlers = handler_registry.get_handlers(EnumMessageCategory.COMMAND)
        assert handlers == []

    def test_get_handler_by_id_found(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should return handler when found by ID."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.freeze()

        handler = handler_registry.get_handler_by_id("event-reducer-handler")
        assert handler is event_reducer_handler

    def test_get_handler_by_id_not_found(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should return None when handler ID not found."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.freeze()

        handler = handler_registry.get_handler_by_id("nonexistent-handler")
        assert handler is None


# =============================================================================
# Unregistration Tests
# =============================================================================


@pytest.mark.unit
class TestUnregistration:
    """Tests for handler unregistration."""

    def test_unregister_existing_handler(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """Should unregister existing handler and return True."""
        handler_registry.register_handler(event_reducer_handler)
        assert handler_registry.handler_count == 1

        result = handler_registry.unregister_handler("event-reducer-handler")
        assert result is True
        assert handler_registry.handler_count == 0

    def test_unregister_nonexistent_handler(
        self, handler_registry: ServiceHandlerRegistry
    ) -> None:
        """Should return False when handler not found."""
        result = handler_registry.unregister_handler("nonexistent-handler")
        assert result is False

    def test_unregister_removes_from_category_index(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
        event_orchestrator_handler: MockMessageHandler,
    ) -> None:
        """Unregistered handler should be removed from category index."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.register_handler(event_orchestrator_handler)

        handler_registry.unregister_handler("event-reducer-handler")
        handler_registry.freeze()

        handlers = handler_registry.get_handlers(EnumMessageCategory.EVENT)
        assert len(handlers) == 1
        assert handlers[0].handler_id == "event-orchestrator-handler"


# =============================================================================
# String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestStringRepresentation:
    """Tests for __str__ and __repr__."""

    def test_str_representation(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """__str__ should return formatted summary."""
        handler_registry.register_handler(event_reducer_handler)

        result = str(handler_registry)
        assert "ServiceHandlerRegistry" in result
        assert "handlers=1" in result
        assert "frozen=False" in result

    def test_str_representation_frozen(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """__str__ should show frozen state."""
        handler_registry.register_handler(event_reducer_handler)
        handler_registry.freeze()

        result = str(handler_registry)
        assert "frozen=True" in result

    def test_repr_representation(
        self,
        handler_registry: ServiceHandlerRegistry,
        event_reducer_handler: MockMessageHandler,
    ) -> None:
        """__repr__ should return detailed representation."""
        handler_registry.register_handler(event_reducer_handler)

        result = repr(handler_registry)
        assert "ServiceHandlerRegistry(" in result
        assert "handlers=" in result
        assert "categories=" in result
        assert "event-reducer-handler" in result
