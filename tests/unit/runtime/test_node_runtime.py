#!/usr/bin/env python3
import pytest

"""
EnvelopeRouter Comprehensive Unit Tests - TDD Test Suite (OMN-228)

This module provides TDD-first test coverage for the EnvelopeRouter class,
which serves as a transport-agnostic orchestrator for ONEX nodes. Tests define
the expected behavior and API contract before implementation.

Test Categories:
    - EnvelopeRouter creation and protocol implementation
    - Handler registration (register_handler)
    - Node registration (register_node)
    - Envelope routing (route_envelope)
    - Execution with handler (execute_with_handler)
    - Edge cases and error handling

Coverage Requirements:
    - All public methods must have test coverage
    - Error handling paths must be tested
    - Mock patterns for handler delegation
    - Protocol compliance verified

TDD Note: These tests are written BEFORE the implementation.
The EnvelopeRouter class should be implemented to pass all these tests.

Related:
    - OMN-228: EnvelopeRouter transport-agnostic orchestrator
    - OMN-227: NodeInstance execution wrapper (predecessor)
    - ONEX Four-Node Architecture documentation
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# TEST CLASS: EnvelopeRouter Creation and Protocol Implementation
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterCreation:
    """Tests for EnvelopeRouter class instantiation."""

    def test_create_node_runtime_instance(self) -> None:
        """
        Test creating EnvelopeRouter instance with default configuration.

        EXPECTED BEHAVIOR:
        - EnvelopeRouter can be instantiated without arguments
        - Instance is created successfully without errors
        - Instance has expected default state (empty handlers, empty nodes)
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        assert runtime is not None
        assert isinstance(runtime, EnvelopeRouter)

    def test_node_runtime_implements_protocol(self) -> None:
        """
        Test that EnvelopeRouter implements ProtocolNodeRuntime.

        EXPECTED BEHAVIOR:
        - EnvelopeRouter instance passes runtime_checkable protocol check
        - EnvelopeRouter has execute_with_handler method
        - Method signature matches ProtocolNodeRuntime specification
        """
        from omnibase_core.runtime import EnvelopeRouter, ProtocolNodeRuntime

        runtime = EnvelopeRouter()

        # Protocol compliance check
        assert isinstance(runtime, ProtocolNodeRuntime)

        # Verify method exists
        assert hasattr(runtime, "execute_with_handler")
        assert callable(runtime.execute_with_handler)


# =============================================================================
# TEST CLASS: Handler Registration
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterRegisterHandler:
    """Tests for EnvelopeRouter register_handler() method."""

    def test_register_handler_stores_by_handler_type(
        self,
        mock_handler: MagicMock,
    ) -> None:
        """
        Test that register_handler stores handler by EnumHandlerType key.

        EXPECTED BEHAVIOR:
        - Handler is stored using its handler_type as key
        - Handler can be retrieved later by handler_type
        - Registration returns None or self for chaining
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Register handler
        result = runtime.register_handler(mock_handler)

        # register_handler returns None (no chaining)
        assert result is None

        # Verify handler is registered
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

    def test_register_handler_accepts_protocol_handler(
        self,
        mock_handler: MagicMock,
    ) -> None:
        """
        Test that register_handler accepts handler implementing ProtocolHandler.

        EXPECTED BEHAVIOR:
        - Handler with handler_type property is accepted
        - Handler with execute method is accepted
        - Handler with describe method is accepted
        - Exactly ONE handler is registered after registration
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Verify mock has required interface
        assert hasattr(mock_handler, "handler_type")
        assert hasattr(mock_handler, "execute")
        assert hasattr(mock_handler, "describe")

        # Should not raise
        runtime.register_handler(mock_handler)

        # Verify exactly ONE handler was registered (explicit count assertion)
        assert len(runtime._handlers) == 1
        # Verify handler is registered with correct handler_type key
        assert mock_handler.handler_type in runtime._handlers
        # Verify the actual handler instance is stored (not a copy or different object)
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

    def test_register_handler_replaces_existing(
        self,
        mock_handler: MagicMock,
        mock_handler_alternate: MagicMock,
    ) -> None:
        """
        Test that registering a handler with same type replaces existing.

        EXPECTED BEHAVIOR:
        - Second handler registration with same type replaces first
        - Only one handler per handler_type is stored
        - No error raised on replacement
        - Old handler is completely removed from registry
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Register first handler
        runtime.register_handler(mock_handler)

        # Verify first handler is registered before replacement
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # Register second handler with same type (should replace)
        runtime.register_handler(mock_handler_alternate)

        # Verify only ONE handler is registered (replacement, not addition)
        assert len(runtime._handlers) == 1

        # Verify the NEW handler is in the registry
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler_alternate

        # Verify the OLD handler is NO LONGER in the registry
        assert mock_handler not in runtime._handlers.values()
        # Verify the NEW handler IS in the registry
        assert mock_handler_alternate in runtime._handlers.values()

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Verify replacement by routing and checking which handler is returned
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=ModelSemVer(major=1, minor=0, patch=0),
            correlation_id=uuid4(),
            source_node="test",
            operation="TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )
        result = runtime.route_envelope(envelope)
        # Alternate handler should have 'alternate' key in describe()
        assert result["handler"].describe().get("alternate") is True
        # Verify the returned handler is the NEW handler (not the old one)
        assert result["handler"] is mock_handler_alternate
        assert result["handler"] is not mock_handler

    def test_register_handler_replace_false_raises_on_duplicate(
        self,
        mock_handler: MagicMock,
        mock_handler_alternate: MagicMock,
    ) -> None:
        """
        Test that replace=False raises error on duplicate handler_type.

        EXPECTED BEHAVIOR:
        - First registration with replace=False succeeds
        - Second registration with same handler_type and replace=False raises ModelOnexError
        - Error code is DUPLICATE_REGISTRATION
        - Error message mentions the handler type
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # First registration with replace=False succeeds
        runtime.register_handler(mock_handler, replace=False)
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers

        # Second registration with same type and replace=False raises error
        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(mock_handler_alternate, replace=False)

        # Verify error details
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
        assert "already registered" in str(error).lower()

        # Verify original handler is still registered (no side effects from failed registration)
        assert len(runtime._handlers) == 1
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

    def test_register_handler_replace_true_replaces_silently(
        self,
        mock_handler: MagicMock,
        mock_handler_alternate: MagicMock,
    ) -> None:
        """
        Test that replace=True (default) silently replaces existing handler.

        EXPECTED BEHAVIOR:
        - First handler is registered successfully
        - Second handler with same type and replace=True replaces the first
        - No error is raised
        - Only one handler remains registered
        - The new handler is the one registered
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Register first handler
        runtime.register_handler(mock_handler)

        # Verify first handler is registered
        assert len(runtime._handlers) == 1
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # Register second handler with explicit replace=True
        runtime.register_handler(mock_handler_alternate, replace=True)

        # Verify replacement occurred
        assert len(runtime._handlers) == 1
        assert runtime._handlers[mock_handler.handler_type] is mock_handler_alternate
        assert mock_handler not in runtime._handlers.values()

    def test_register_handler_none_raises_error(self) -> None:
        """
        Test that registering None handler raises error.

        EXPECTED BEHAVIOR:
        - None handler raises ValueError or TypeError
        - Error message indicates handler is required
        - No handlers are registered after failed registration
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Verify empty state before attempted registration
        assert len(runtime._handlers) == 0

        with pytest.raises((ValueError, TypeError, ModelOnexError)):
            runtime.register_handler(None)  # type: ignore[arg-type]

        # Verify no handlers were registered after failed registration
        assert len(runtime._handlers) == 0


# =============================================================================
# TEST CLASS: Node Registration
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterRegisterNode:
    """Tests for EnvelopeRouter register_node() method."""

    def test_register_node_stores_by_slug(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that register_node stores node by slug.

        EXPECTED BEHAVIOR:
        - Node is stored using its slug as key
        - Node can be retrieved later by slug
        - Registration returns None or self for chaining
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        result = runtime.register_node(instance)

        # register_node returns None (no chaining)
        assert result is None

        # Verify node was registered with correct slug key
        assert len(runtime._nodes) == 1
        assert sample_slug in runtime._nodes
        # Verify the actual instance is stored (not a copy or different object)
        assert runtime._nodes[sample_slug] is instance
        # Verify node properties are preserved
        assert runtime._nodes[sample_slug].slug == sample_slug
        assert runtime._nodes[sample_slug].node_type == sample_node_type

    def test_register_node_accepts_runtime_node_instance(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that register_node accepts EnvelopeRouterInstance.

        EXPECTED BEHAVIOR:
        - EnvelopeRouterInstance is accepted without error
        - Instance properties (slug, node_type, contract) are preserved
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Should not raise
        runtime.register_node(instance)

        # Verify node was registered with correct properties
        assert len(runtime._nodes) == 1
        assert sample_slug in runtime._nodes
        registered_node = runtime._nodes[sample_slug]
        # Verify identity - same object, not a copy
        assert registered_node is instance
        # Verify all properties are preserved
        assert registered_node.slug == sample_slug
        assert registered_node.node_type == sample_node_type
        assert registered_node.contract is mock_contract

    def test_register_node_duplicate_slug_raises_error(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that registering node with duplicate slug raises error.

        EXPECTED BEHAVIOR:
        - First registration succeeds
        - Second registration with same slug raises ModelOnexError
        - Error message mentions duplicate slug
        - Original node is still registered (no side effects from failed registration)
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        instance1 = NodeInstance(
            slug="duplicate-slug",
            node_type=sample_node_type,
            contract=mock_contract,
        )

        instance2 = NodeInstance(
            slug="duplicate-slug",  # Same slug
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # First registration succeeds
        runtime.register_node(instance1)

        # Verify first node is registered
        assert len(runtime._nodes) == 1
        assert "duplicate-slug" in runtime._nodes
        assert runtime._nodes["duplicate-slug"] is instance1

        # Second registration raises error
        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_node(instance2)

        assert (
            "duplicate" in str(exc_info.value).lower()
            or "already" in str(exc_info.value).lower()
        )

        # Verify original node is still registered (no side effects from failed registration)
        assert len(runtime._nodes) == 1
        assert runtime._nodes["duplicate-slug"] is instance1
        # Verify the second instance was NOT registered (check by identity, not equality)
        # Note: instance1 and instance2 have same values but are different objects
        registered_values = list(runtime._nodes.values())
        assert all(val is instance1 for val in registered_values)
        assert not any(val is instance2 for val in registered_values)

    def test_register_node_none_raises_error(self) -> None:
        """
        Test that registering None node raises error.

        EXPECTED BEHAVIOR:
        - None node raises ValueError or TypeError
        - Error message indicates node is required
        - No nodes are registered after failed registration
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Verify empty state before attempted registration
        assert len(runtime._nodes) == 0

        with pytest.raises((ValueError, TypeError, ModelOnexError)):
            runtime.register_node(None)  # type: ignore[arg-type]

        # Verify no nodes were registered after failed registration
        assert len(runtime._nodes) == 0


# =============================================================================
# TEST CLASS: Route Envelope
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterRouteEnvelope:
    """Tests for EnvelopeRouter route_envelope() method."""

    def test_route_envelope_returns_handler_for_handler_type(
        self,
        mock_handler: MagicMock,
        sample_envelope: ModelOnexEnvelope,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope returns correct handler for handler_type.

        EXPECTED BEHAVIOR:
        - Envelope with handler_type returns matching handler
        - Returned handler matches registered handler
        - Routing metadata is included in return value
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler was registered before routing
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Create envelope with handler_type matching mock_handler
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Route should return handler and metadata
        result = runtime.route_envelope(envelope)

        # Result should contain handler
        assert result is not None
        assert "handler" in result or hasattr(result, "handler")
        # Verify the correct handler is returned
        assert result["handler"] is mock_handler

    def test_route_envelope_no_matching_handler_raises_error(
        self,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope raises error when no handler matches.

        EXPECTED BEHAVIOR:
        - Envelope with unregistered handler_type raises ModelOnexError
        - Error message indicates no handler found
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # CRITICAL: freeze before routing (even with no handlers)
        runtime.freeze()

        # Create envelope with handler_type but no handler registered
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,  # Not registered
        )

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.route_envelope(envelope)

        error_msg = str(exc_info.value).lower()
        assert "handler" in error_msg or "not found" in error_msg

    def test_route_envelope_with_envelope_handler_type(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test routing based on envelope's handler_type field.

        EXPECTED BEHAVIOR:
        - Envelope with explicit handler_type routes to matching handler
        - handler_type field is used for routing decision
        - Returned handler is the exact instance that was registered
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration before routing
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Envelope explicitly specifies handler_type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        result = runtime.route_envelope(envelope)

        assert result is not None
        # Verify the handler returned is the exact instance we registered
        assert "handler" in result
        assert result["handler"] is mock_handler
        # Verify handler_type matches what was requested
        assert result["handler"].handler_type == mock_handler.handler_type

    def test_route_envelope_with_string_handler_type_raises_error(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope raises error when handler_type is a string.

        EXPECTED BEHAVIOR:
        - Envelope with string handler_type raises ModelOnexError
        - Error code is INVALID_PARAMETER
        - Error message indicates expected EnumHandlerType
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Create envelope with handler_type set correctly, then mutate to invalid type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Force invalid type using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(envelope, "handler_type", "HTTP")

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.route_envelope(envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        error_msg = str(exc_info.value)
        assert "EnumHandlerType" in error_msg
        assert "str" in error_msg

    def test_route_envelope_with_none_handler_type_raises_error(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope raises error when handler_type is None.

        EXPECTED BEHAVIOR:
        - Envelope with None handler_type raises ModelOnexError
        - Error code is INVALID_PARAMETER
        - Error message indicates handler_type is required
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Create envelope without handler_type (defaults to None)
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=None,  # Explicitly None
        )

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.route_envelope(envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        error_msg = str(exc_info.value).lower()
        assert "handler_type" in error_msg

    def test_route_envelope_with_integer_handler_type_raises_error(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope raises error when handler_type is an integer.

        EXPECTED BEHAVIOR:
        - Envelope with integer handler_type raises ModelOnexError
        - Error code is INVALID_PARAMETER
        - Error message indicates expected EnumHandlerType
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Create envelope with valid handler_type, then mutate to invalid type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Force invalid type using object.__setattr__ to bypass Pydantic validation
        object.__setattr__(envelope, "handler_type", 42)

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.route_envelope(envelope)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER
        error_msg = str(exc_info.value)
        assert "EnumHandlerType" in error_msg
        assert "int" in error_msg


# =============================================================================
# TEST CLASS: Execute With Handler
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestEnvelopeRouterExecuteWithHandler:
    """Tests for EnvelopeRouter execute_with_handler() method.

    Note:
    - Extended timeout (60s) for async handler execution tests
    """

    @pytest.mark.asyncio
    async def test_execute_with_handler_calls_route_envelope(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execute_with_handler internally routes envelope.

        EXPECTED BEHAVIOR:
        - execute_with_handler uses route_envelope to find handler
        - Routing is based on envelope handler_type
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration before execution
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        # Create envelope with handler_type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Execute should succeed (routes internally)
        result = await runtime.execute_with_handler(envelope, instance)

        assert result is not None
        # Verify result is a valid response envelope
        assert isinstance(result, ModelOnexEnvelope)
        assert result.is_response is True

    @pytest.mark.asyncio
    async def test_execute_with_handler_calls_handler_execute(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execute_with_handler calls the handler's execute method.

        EXPECTED BEHAVIOR:
        - Handler.execute() is called with envelope
        - Handler receives the correct envelope data
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        await runtime.execute_with_handler(envelope, instance)

        # Verify handler.execute was called
        mock_handler.execute.assert_called_once()

        # Verify envelope was passed
        call_args = mock_handler.execute.call_args
        assert call_args is not None
        passed_envelope = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("envelope")
        )
        assert passed_envelope is not None

    @pytest.mark.asyncio
    async def test_execute_with_handler_returns_response_envelope(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execute_with_handler returns a response envelope.

        EXPECTED BEHAVIOR:
        - Return value is ModelOnexEnvelope
        - Response envelope has is_response=True
        - Response envelope has correlation_id matching request
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        correlation_id = uuid4()
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=correlation_id,
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        result = await runtime.execute_with_handler(envelope, instance)

        # Result should be an envelope
        assert isinstance(result, ModelOnexEnvelope)

        # Should be marked as response
        assert result.is_response is True

        # Should preserve correlation_id
        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_execute_with_handler_without_handler_type_raises_error(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that envelope without handler_type raises error.

        EXPECTED BEHAVIOR:
        - Envelope with handler_type=None raises ModelOnexError
        - Error message indicates handler_type is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        # Envelope without handler_type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=None,  # Explicitly None
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await runtime.execute_with_handler(envelope, instance)

        error_msg = str(exc_info.value).lower()
        assert "handler" in error_msg or "type" in error_msg


# =============================================================================
# TEST CLASS: Edge Cases and Error Handling
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestEnvelopeRouterEdgeCases:
    """Tests for EnvelopeRouter edge cases and error conditions.

    Note:
    - Extended timeout (60s) for async error handling tests
    """

    @pytest.mark.asyncio
    async def test_execute_without_registered_handlers_raises_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execution without any registered handlers raises error.

        EXPECTED BEHAVIOR:
        - Runtime with no handlers raises ModelOnexError
        - Error indicates no handlers available
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()  # No handlers registered

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,
        )

        with pytest.raises(ModelOnexError):
            await runtime.execute_with_handler(envelope, instance)

    def test_multiple_handlers_registered(
        self,
        mock_handler: MagicMock,
        mock_handler_database: MagicMock,
        mock_handler_kafka: MagicMock,
    ) -> None:
        """
        Test registering multiple handlers with different types.

        EXPECTED BEHAVIOR:
        - Multiple handlers with different types can be registered
        - Each handler is stored separately by type
        - Routing selects correct handler for each type
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Register multiple handlers
        runtime.register_handler(mock_handler)  # HTTP
        runtime.register_handler(mock_handler_database)  # DATABASE
        runtime.register_handler(mock_handler_kafka)  # KAFKA

        # Verify exact count of handlers registered
        assert len(runtime._handlers) == 3

        # Verify each handler type is stored correctly
        assert EnumHandlerType.HTTP in runtime._handlers
        assert EnumHandlerType.DATABASE in runtime._handlers
        assert EnumHandlerType.KAFKA in runtime._handlers

        # CRITICAL: freeze before routing
        runtime.freeze()

        # Verify each handler type can be routed
        for handler in [mock_handler, mock_handler_database, mock_handler_kafka]:
            envelope = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=ModelSemVer(major=1, minor=0, patch=0),
                correlation_id=uuid4(),
                source_node="test",
                operation="TEST",
                payload={},
                timestamp=datetime.now(UTC),
                handler_type=handler.handler_type,
            )
            result = runtime.route_envelope(envelope)
            assert result["handler"] is handler

    @pytest.mark.asyncio
    async def test_handler_execution_error_returns_error_envelope(
        self,
        mock_handler_with_error: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that handler execution error returns error envelope.

        EXPECTED BEHAVIOR:
        - When handler.execute() raises, error envelope is returned
        - Error envelope has success=False
        - Error envelope has error message
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler_with_error)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler_with_error.handler_type in runtime._handlers
        assert (
            runtime._handlers[mock_handler_with_error.handler_type]
            is mock_handler_with_error
        )

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler_with_error.handler_type,
        )

        result = await runtime.execute_with_handler(envelope, instance)

        # Should return error envelope (not raise)
        assert isinstance(result, ModelOnexEnvelope)
        assert result.is_response is True
        assert result.success is False
        assert result.error is not None

    def test_register_handler_with_invalid_type_raises_error(self) -> None:
        """
        Test that handler without proper handler_type raises error.

        EXPECTED BEHAVIOR:
        - Handler without handler_type property raises error
        - Error message indicates invalid handler
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler without handler_type
        invalid_handler = MagicMock(spec=[])  # No handler_type attribute

        with pytest.raises((AttributeError, ModelOnexError, TypeError)):
            runtime.register_handler(invalid_handler)

    def test_register_handler_without_execute_method_raises_error(self) -> None:
        """
        Test that handler without callable execute method raises error.

        EXPECTED BEHAVIOR:
        - Handler with handler_type but missing execute method raises ModelOnexError
        - Error message indicates execute method is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler with handler_type but no execute method
        invalid_handler = MagicMock(spec=["handler_type", "describe"])
        invalid_handler.handler_type = EnumHandlerType.HTTP
        invalid_handler.describe = MagicMock(return_value={})

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(invalid_handler)

        assert "execute" in str(exc_info.value).lower()

    def test_register_handler_without_describe_method_raises_error(self) -> None:
        """
        Test that handler without callable describe method raises error.

        EXPECTED BEHAVIOR:
        - Handler with handler_type and execute but missing describe raises ModelOnexError
        - Error message indicates describe method is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler with handler_type and execute, but no describe method
        invalid_handler = MagicMock(spec=["handler_type", "execute"])
        invalid_handler.handler_type = EnumHandlerType.HTTP
        invalid_handler.execute = MagicMock()

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(invalid_handler)

        assert "describe" in str(exc_info.value).lower()

    def test_register_handler_with_non_callable_execute_raises_error(self) -> None:
        """
        Test that handler with non-callable execute attribute raises error.

        EXPECTED BEHAVIOR:
        - Handler with execute as non-callable (e.g., string) raises ModelOnexError
        - Error message indicates execute must be callable
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler with non-callable execute
        invalid_handler = MagicMock()
        invalid_handler.handler_type = EnumHandlerType.HTTP
        invalid_handler.execute = "not_callable"  # String, not callable
        invalid_handler.describe = MagicMock(return_value={})

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(invalid_handler)

        assert "execute" in str(exc_info.value).lower()

    def test_register_handler_with_non_callable_describe_raises_error(self) -> None:
        """
        Test that handler with non-callable describe attribute raises error.

        EXPECTED BEHAVIOR:
        - Handler with describe as non-callable (e.g., string) raises ModelOnexError
        - Error message indicates describe must be callable
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler with non-callable describe
        invalid_handler = MagicMock()
        invalid_handler.handler_type = EnumHandlerType.HTTP
        invalid_handler.execute = MagicMock()
        invalid_handler.describe = "not_callable"  # String, not callable

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(invalid_handler)

        assert "describe" in str(exc_info.value).lower()

    def test_register_handler_with_missing_handler_type_property_raises_error(
        self,
    ) -> None:
        """
        Test that handler without handler_type property raises ModelOnexError.

        EXPECTED BEHAVIOR:
        - Handler without handler_type property raises ModelOnexError (not AttributeError)
        - Error message indicates handler_type property is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Create handler without handler_type using spec to restrict attributes
        invalid_handler = MagicMock(spec=["execute", "describe"])
        invalid_handler.execute = MagicMock()
        invalid_handler.describe = MagicMock(return_value={})

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(invalid_handler)

        assert "handler_type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_none_envelope_raises_error(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that execute_with_handler with None envelope raises error.

        EXPECTED BEHAVIOR:
        - None envelope raises ModelOnexError or TypeError
        - Error message indicates envelope is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        with pytest.raises((ModelOnexError, TypeError, AttributeError)):
            await runtime.execute_with_handler(None, instance)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_execute_with_none_instance_raises_error(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execute_with_handler with None instance raises error.

        EXPECTED BEHAVIOR:
        - None instance raises ModelOnexError or TypeError
        - Error message indicates instance is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        with pytest.raises((ModelOnexError, TypeError, AttributeError)):
            await runtime.execute_with_handler(envelope, None)  # type: ignore[arg-type]


# =============================================================================
# TEST CLASS: String Representation
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterStringRepresentation:
    """Tests for EnvelopeRouter __str__ and __repr__ methods."""

    def test_str_representation_empty_router(self) -> None:
        """
        Test that string representation shows zero counts for empty router.

        EXPECTED BEHAVIOR:
        - str(runtime) shows "EnvelopeRouter[handlers=0, nodes=0]" format
        - Contains class name identifier
        - Shows correct counts (0 for empty router)
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        str_repr = str(runtime)

        assert str_repr is not None
        assert len(str_repr) > 0
        assert "EnvelopeRouter" in str_repr
        assert "handlers=0" in str_repr
        assert "nodes=0" in str_repr

    def test_str_representation_with_handlers_and_nodes(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that string representation shows correct counts after registration.

        EXPECTED BEHAVIOR:
        - str(runtime) reflects accurate handler and node counts
        - Format is "EnvelopeRouter[handlers=N, nodes=M]"
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration before proceeding
        assert len(runtime._handlers) == 1

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

        # Verify node registration before checking string representation
        assert len(runtime._nodes) == 1

        str_repr = str(runtime)

        assert "EnvelopeRouter" in str_repr
        assert "handlers=1" in str_repr
        assert "nodes=1" in str_repr

    def test_repr_provides_debug_info_empty_router(self) -> None:
        """
        Test that repr shows empty collections for empty router.

        EXPECTED BEHAVIOR:
        - repr(runtime) includes class name
        - Shows empty handler list []
        - Shows empty node list []
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        repr_str = repr(runtime)

        assert "EnvelopeRouter" in repr_str
        assert "handlers=[]" in repr_str
        assert "nodes=[]" in repr_str

    def test_repr_provides_debug_info_with_handlers(
        self,
        mock_handler: MagicMock,
    ) -> None:
        """
        Test that repr includes handler type information.

        EXPECTED BEHAVIOR:
        - repr(runtime) includes class name
        - Shows registered handler types in the list
        - Handler type value is visible in output
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration before checking repr
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers

        repr_str = repr(runtime)

        assert "EnvelopeRouter" in repr_str
        # Should include the handler type value (e.g., 'http')
        assert mock_handler.handler_type.value in repr_str.lower()

    def test_repr_provides_debug_info_with_nodes(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that repr includes node slug information.

        EXPECTED BEHAVIOR:
        - repr(runtime) includes class name
        - Shows registered node slugs in the list
        - Node slug is visible in output
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration before node registration
        assert len(runtime._handlers) == 1

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

        # Verify both handler and node registrations
        assert len(runtime._handlers) == 1
        assert len(runtime._nodes) == 1

        repr_str = repr(runtime)

        assert "EnvelopeRouter" in repr_str
        # Should include the node slug
        assert sample_slug in repr_str

    def test_repr_multiple_handlers_shows_all_types(
        self,
        mock_handler: MagicMock,
        mock_handler_database: MagicMock,
        mock_handler_kafka: MagicMock,
    ) -> None:
        """
        Test that repr shows all handler types when multiple are registered.

        EXPECTED BEHAVIOR:
        - All registered handler types are visible in repr
        - Each handler type value appears in the output
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.register_handler(mock_handler_database)
        runtime.register_handler(mock_handler_kafka)

        # Verify all 3 handlers are registered with correct count
        assert len(runtime._handlers) == 3
        assert EnumHandlerType.HTTP in runtime._handlers
        assert EnumHandlerType.DATABASE in runtime._handlers
        assert EnumHandlerType.KAFKA in runtime._handlers

        repr_str = repr(runtime)

        assert "EnvelopeRouter" in repr_str
        # All handler types should be visible
        assert mock_handler.handler_type.value in repr_str.lower()
        assert mock_handler_database.handler_type.value in repr_str.lower()
        assert mock_handler_kafka.handler_type.value in repr_str.lower()


# =============================================================================
# TEST CLASS: Integration Patterns
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestEnvelopeRouterIntegrationPatterns:
    """Tests for common EnvelopeRouter usage patterns.

    Note:
    - Extended timeout (60s) for async integration tests
    """

    @pytest.mark.asyncio
    async def test_full_lifecycle_pattern(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test full lifecycle: create -> register -> execute.

        EXPECTED BEHAVIOR:
        - Complete workflow executes without errors
        - Each step completes successfully
        - Registration state is verified at each step
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        # Create runtime
        runtime = EnvelopeRouter()

        # Verify initial empty state
        assert len(runtime._handlers) == 0
        assert len(runtime._nodes) == 0

        # Register handler
        runtime.register_handler(mock_handler)

        # Verify handler registration
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        # Create and register node
        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

        # Verify node registration
        assert len(runtime._nodes) == 1
        assert sample_slug in runtime._nodes
        assert runtime._nodes[sample_slug] is instance

        # CRITICAL: freeze before execution
        runtime.freeze()

        # Create envelope
        correlation_id = uuid4()
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=correlation_id,
            source_node="test_source",
            target_node=sample_slug,
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Execute
        result = await runtime.execute_with_handler(envelope, instance)

        # Verify result
        assert isinstance(result, ModelOnexEnvelope)
        assert result.is_response is True
        assert result.correlation_id == correlation_id
        # Verify handler was invoked
        mock_handler.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_executions_same_runtime(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test multiple executions using the same runtime.

        EXPECTED BEHAVIOR:
        - Runtime can handle multiple envelope executions
        - State is maintained correctly across executions
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        # Execute multiple times
        for i in range(3):
            envelope = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=uuid4(),
                source_node="test_source",
                operation=f"TEST_OP_{i}",
                payload={"iteration": i},
                timestamp=datetime.now(UTC),
                handler_type=mock_handler.handler_type,
            )

            result = await runtime.execute_with_handler(envelope, instance)
            assert result.is_response is True

        # Handler should have been called 3 times
        assert mock_handler.execute.call_count == 3

    def test_runtime_with_multiple_node_types(
        self,
        mock_handler: MagicMock,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test runtime with nodes of different types.

        EXPECTED BEHAVIOR:
        - Nodes with different EnumNodeType can be registered
        - Each node is stored separately by slug
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Verify handler registration was successful
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

        node_types = [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.EFFECT_GENERIC,
            EnumNodeType.REDUCER_GENERIC,
            EnumNodeType.ORCHESTRATOR_GENERIC,
        ]

        for i, node_type in enumerate(node_types):
            instance = NodeInstance(
                slug=f"node-{node_type.value}-{i}",
                node_type=node_type,
                contract=mock_contract,
            )
            runtime.register_node(instance)

        # All nodes should be registered with explicit count assertion
        assert len(runtime._nodes) == len(node_types)  # Should be 4
        assert len(runtime._nodes) == 4  # Explicit count for clarity

        # Verify each node is stored by its unique slug
        for i, node_type in enumerate(node_types):
            expected_slug = f"node-{node_type.value}-{i}"
            assert expected_slug in runtime._nodes
            assert runtime._nodes[expected_slug].node_type == node_type


# =============================================================================
# TEST CLASS: Freeze Functionality
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterFreeze:
    """Tests for EnvelopeRouter freeze() method and is_frozen property."""

    def test_is_frozen_initially_false(self) -> None:
        """
        Test that is_frozen property is False on new router.

        EXPECTED BEHAVIOR:
        - New router instance has is_frozen=False
        - Registration is allowed before freeze
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        assert runtime.is_frozen is False

    def test_freeze_sets_is_frozen_to_true(self) -> None:
        """
        Test that freeze() sets is_frozen to True.

        EXPECTED BEHAVIOR:
        - Calling freeze() transitions is_frozen from False to True
        - Property reflects the frozen state after freeze() call
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Initial state
        assert runtime.is_frozen is False

        # Freeze the router
        runtime.freeze()

        # Verify frozen state
        assert runtime.is_frozen is True

    def test_freeze_is_idempotent(self) -> None:
        """
        Test that calling freeze() multiple times has no additional effect.

        EXPECTED BEHAVIOR:
        - Multiple freeze() calls do not raise errors
        - is_frozen remains True after multiple freeze() calls
        - Router state is unchanged by subsequent freeze() calls
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # First freeze
        runtime.freeze()
        assert runtime.is_frozen is True

        # Second freeze (should be idempotent)
        runtime.freeze()
        assert runtime.is_frozen is True

        # Third freeze (should still be idempotent)
        runtime.freeze()
        assert runtime.is_frozen is True

    def test_register_handler_raises_invalid_state_after_freeze(
        self,
        mock_handler: MagicMock,
    ) -> None:
        """
        Test that register_handler raises INVALID_STATE after freeze.

        EXPECTED BEHAVIOR:
        - Calling register_handler() after freeze() raises ModelOnexError
        - Error code is INVALID_STATE
        - Error message mentions frozen state
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.freeze()

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(mock_handler)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "frozen" in str(error).lower()

    def test_register_node_raises_invalid_state_after_freeze(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that register_node raises INVALID_STATE after freeze.

        EXPECTED BEHAVIOR:
        - Calling register_node() after freeze() raises ModelOnexError
        - Error code is INVALID_STATE
        - Error message mentions frozen state
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.freeze()

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_node(instance)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "frozen" in str(error).lower()

    def test_routing_works_after_freeze(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that routing works correctly after freeze.

        EXPECTED BEHAVIOR:
        - route_envelope() works normally after freeze()
        - Frozen router can still route envelopes to registered handlers
        - Read operations are not affected by frozen state
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.freeze()

        # Create envelope for routing
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Routing should work after freeze
        result = runtime.route_envelope(envelope)

        assert result is not None
        assert result["handler"] is mock_handler
        assert result["handler_type"] == mock_handler.handler_type

    @pytest.mark.asyncio
    async def test_execution_works_after_freeze(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that execute_with_handler works correctly after freeze.

        EXPECTED BEHAVIOR:
        - execute_with_handler() works normally after freeze()
        - Frozen router can still execute envelopes with handlers
        - Handler is called and response is returned correctly
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

        # Freeze after registration
        runtime.freeze()

        # Create envelope for execution
        correlation_id = uuid4()
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=correlation_id,
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Execution should work after freeze
        result = await runtime.execute_with_handler(envelope, instance)

        assert isinstance(result, ModelOnexEnvelope)
        assert result.is_response is True
        assert result.correlation_id == correlation_id
        mock_handler.execute.assert_called_once()

    def test_freeze_before_registration_prevents_all_registration(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that freezing an empty router prevents all registration.

        EXPECTED BEHAVIOR:
        - Freezing empty router succeeds
        - Both handler and node registration raise INVALID_STATE
        - Router remains empty after failed registrations
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Freeze immediately (empty router)
        runtime.freeze()
        assert runtime.is_frozen is True
        assert len(runtime._handlers) == 0
        assert len(runtime._nodes) == 0

        # Handler registration should fail
        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_handler(mock_handler)
        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

        # Node registration should fail
        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            runtime.register_node(instance)
        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE

        # Verify router is still empty
        assert len(runtime._handlers) == 0
        assert len(runtime._nodes) == 0

    def test_str_representation_shows_frozen_state(
        self,
        mock_handler: MagicMock,
    ) -> None:
        """
        Test that __str__ includes frozen state.

        EXPECTED BEHAVIOR:
        - String representation shows frozen=False before freeze
        - String representation shows frozen=True after freeze
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Before freeze
        str_before = str(runtime)
        assert "frozen=False" in str_before

        # After freeze
        runtime.freeze()
        str_after = str(runtime)
        assert "frozen=True" in str_after

    def test_freeze_register_handler_preserves_existing_handlers(
        self,
        mock_handler: MagicMock,
        mock_handler_database: MagicMock,
    ) -> None:
        """
        Test that failed registration after freeze preserves existing handlers.

        EXPECTED BEHAVIOR:
        - Handlers registered before freeze are preserved
        - Failed registration after freeze does not modify handler registry
        - Existing handlers remain accessible
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.freeze()

        # Verify handler is registered
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers

        # Attempt to register another handler (should fail)
        with pytest.raises(ModelOnexError):
            runtime.register_handler(mock_handler_database)

        # Original handler should still be registered
        assert len(runtime._handlers) == 1
        assert mock_handler.handler_type in runtime._handlers
        assert runtime._handlers[mock_handler.handler_type] is mock_handler

    def test_freeze_register_node_preserves_existing_nodes(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Test that failed registration after freeze preserves existing nodes.

        EXPECTED BEHAVIOR:
        - Nodes registered before freeze are preserved
        - Failed registration after freeze does not modify node registry
        - Existing nodes remain accessible
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        instance1 = NodeInstance(
            slug="original-node",
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance1)
        runtime.freeze()

        # Verify node is registered
        assert len(runtime._nodes) == 1
        assert "original-node" in runtime._nodes

        # Attempt to register another node (should fail)
        instance2 = NodeInstance(
            slug="new-node",
            node_type=sample_node_type,
            contract=mock_contract,
        )
        with pytest.raises(ModelOnexError):
            runtime.register_node(instance2)

        # Original node should still be registered
        assert len(runtime._nodes) == 1
        assert "original-node" in runtime._nodes
        assert runtime._nodes["original-node"] is instance1

    def test_route_envelope_before_freeze_raises_invalid_state(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope() raises INVALID_STATE when called before freeze().

        EXPECTED BEHAVIOR:
        - Calling route_envelope() before freeze() raises ModelOnexError
        - Error code is INVALID_STATE
        - Error message mentions freeze requirement
        - This enforces the freeze contract for thread safety

        This test addresses PR #145 review feedback to verify the freeze contract
        is properly enforced at runtime.
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        # Create envelope with valid handler_type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Attempting to route before freeze should raise INVALID_STATE
        with pytest.raises(ModelOnexError) as exc_info:
            runtime.route_envelope(envelope)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.INVALID_STATE
        error_msg = str(error).lower()
        assert "freeze" in error_msg

    def test_route_envelope_after_freeze_succeeds(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that route_envelope() succeeds when called after freeze().

        EXPECTED BEHAVIOR:
        - Calling freeze() enables route_envelope() to work
        - Routing returns the correct handler and handler_type
        - The freeze contract allows read operations after freezing

        This is the positive case complementing test_route_envelope_before_freeze_raises_invalid_state.
        """
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.freeze()  # CRITICAL: freeze before routing

        # Create envelope with valid handler_type
        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test_source",
            operation="TEST_OPERATION",
            payload={"test": "data"},
            timestamp=datetime.now(UTC),
            handler_type=mock_handler.handler_type,
        )

        # Should succeed after freeze
        result = runtime.route_envelope(envelope)

        assert result is not None
        assert "handler" in result
        assert result["handler"] is mock_handler
        assert "handler_type" in result
        assert result["handler_type"] == mock_handler.handler_type


# =============================================================================
# TEST CLASS: Large Registry Repr Behavior
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterLargeRegistryRepr:
    """
    Tests for __repr__ behavior with large registries.

    The EnvelopeRouter uses threshold-based abbreviation for __repr__ output:
    - At or below threshold (10): Shows full list of handler types / node slugs
    - Above threshold (>10): Shows abbreviated count format like '<11 handlers>'

    This prevents repr output from becoming unwieldy with large registries
    while still providing useful debugging information.
    """

    def test_repr_threshold_value_is_10(self) -> None:
        """
        Test that _REPR_ITEM_THRESHOLD is set to 10.

        EXPECTED BEHAVIOR:
        - EnvelopeRouter._REPR_ITEM_THRESHOLD == 10
        - This test documents the expected threshold value
        """
        from omnibase_core.runtime import EnvelopeRouter

        assert EnvelopeRouter._REPR_ITEM_THRESHOLD == 10

    def test_repr_nodes_at_threshold_shows_full_list(
        self,
        mock_contract: MagicMock,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test __repr__ shows full list when at threshold (10 nodes).

        EXPECTED BEHAVIOR:
        - With exactly 10 nodes, repr shows full slug list
        - All 10 slugs are visible in output
        - Should NOT show abbreviated count format
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Register exactly 10 nodes (at threshold)
        for i in range(10):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime.register_node(instance)

        repr_str = repr(runtime)

        # All slugs should be visible in the repr output
        for i in range(10):
            assert f"node-{i}" in repr_str, f"node-{i} should be in repr output"

        # Should NOT show abbreviated count format
        assert "<10 nodes>" not in repr_str
        # The nodes should be in a list format
        assert "nodes=[" in repr_str

    def test_repr_nodes_above_threshold_shows_abbreviated(
        self,
        mock_contract: MagicMock,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test __repr__ shows abbreviated count when above threshold (11 nodes).

        EXPECTED BEHAVIOR:
        - With 11 nodes, repr shows '<11 nodes>' instead of full list
        - Individual slugs are NOT listed in output
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Register 11 nodes (above threshold)
        for i in range(11):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime.register_node(instance)

        repr_str = repr(runtime)

        # Should show abbreviated count
        assert "<11 nodes>" in repr_str

        # Individual slugs should NOT be in a list format
        # (the abbreviated format replaces the list)
        assert "nodes=[" not in repr_str

    def test_repr_handlers_at_threshold_shows_full_list(self) -> None:
        """
        Test __repr__ shows full list when at threshold (10 handlers).

        EXPECTED BEHAVIOR:
        - With exactly 10 handlers, repr shows full handler type list
        - All handler type values are visible in output
        - Should NOT show abbreviated count format
        """
        from unittest.mock import MagicMock

        from omnibase_core.enums.enum_handler_type import EnumHandlerType
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Get all available handler types (there are 12 in EnumHandlerType)
        all_handler_types = list(EnumHandlerType)
        handler_types_to_use = all_handler_types[:10]  # Use exactly 10

        # Register exactly 10 handlers (at threshold)
        for handler_type in handler_types_to_use:
            handler = MagicMock()
            handler.handler_type = handler_type
            handler.execute = MagicMock()
            handler.describe = MagicMock(
                return_value={"name": f"handler_{handler_type.value}"}
            )
            runtime.register_handler(handler)

        repr_str = repr(runtime)

        # All handler type values should be visible in the repr output
        for handler_type in handler_types_to_use:
            assert handler_type.value in repr_str.lower(), (
                f"{handler_type.value} should be in repr output"
            )

        # Should NOT show abbreviated count format
        assert "<10 handlers>" not in repr_str
        # The handlers should be in a list format
        assert "handlers=[" in repr_str

    def test_repr_handlers_above_threshold_shows_abbreviated(self) -> None:
        """
        Test __repr__ shows abbreviated count when above threshold (11 handlers).

        EXPECTED BEHAVIOR:
        - With 11 handlers, repr shows '<11 handlers>' instead of full list
        - Individual handler types are NOT listed in output
        """
        from unittest.mock import MagicMock

        from omnibase_core.enums.enum_handler_type import EnumHandlerType
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Get all available handler types (there are 12 in EnumHandlerType)
        all_handler_types = list(EnumHandlerType)
        handler_types_to_use = all_handler_types[:11]  # Use 11 (above threshold)

        # Register 11 handlers (above threshold)
        for handler_type in handler_types_to_use:
            handler = MagicMock()
            handler.handler_type = handler_type
            handler.execute = MagicMock()
            handler.describe = MagicMock(
                return_value={"name": f"handler_{handler_type.value}"}
            )
            runtime.register_handler(handler)

        repr_str = repr(runtime)

        # Should show abbreviated count
        assert "<11 handlers>" in repr_str

        # Individual handler types should NOT be in a list format
        # (the abbreviated format replaces the list)
        assert "handlers=[" not in repr_str

    def test_repr_large_registry_both_above_threshold(
        self,
        mock_contract: MagicMock,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test __repr__ with both handlers and nodes above threshold.

        EXPECTED BEHAVIOR:
        - With 11 handlers and 15 nodes, both show abbreviated format
        - Format shows '<11 handlers>' and '<15 nodes>'
        - No list formats appear in output
        """
        from unittest.mock import MagicMock

        from omnibase_core.enums.enum_handler_type import EnumHandlerType
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Register 11 handlers (above threshold)
        all_handler_types = list(EnumHandlerType)[:11]
        for handler_type in all_handler_types:
            handler = MagicMock()
            handler.handler_type = handler_type
            handler.execute = MagicMock()
            handler.describe = MagicMock(
                return_value={"name": f"handler_{handler_type.value}"}
            )
            runtime.register_handler(handler)

        # Register 15 nodes (above threshold)
        for i in range(15):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime.register_node(instance)

        repr_str = repr(runtime)

        # Both should show abbreviated counts
        assert "<11 handlers>" in repr_str
        assert "<15 nodes>" in repr_str

        # No list formats should appear
        assert "handlers=[" not in repr_str
        assert "nodes=[" not in repr_str

    def test_repr_mixed_at_and_above_threshold(
        self,
        mock_handler: MagicMock,
        mock_contract: MagicMock,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test __repr__ with handlers at threshold and nodes above threshold.

        EXPECTED BEHAVIOR:
        - With 1 handler (at threshold) and 11 nodes (above threshold)
        - Handlers show full list format
        - Nodes show abbreviated count format
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Register 1 handler (well below threshold)
        runtime.register_handler(mock_handler)

        # Register 11 nodes (above threshold)
        for i in range(11):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime.register_node(instance)

        repr_str = repr(runtime)

        # Handlers should show list format (1 is below threshold)
        assert "handlers=[" in repr_str
        assert mock_handler.handler_type.value in repr_str.lower()

        # Nodes should show abbreviated count
        assert "<11 nodes>" in repr_str
        assert "nodes=[" not in repr_str

    def test_repr_exactly_at_boundary_transitions_correctly(
        self,
        mock_contract: MagicMock,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test that the boundary at 10 items transitions correctly to 11.

        EXPECTED BEHAVIOR:
        - 10 nodes: shows full list
        - 11 nodes: shows abbreviated count
        - Transition is clean with no edge case errors
        """
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        # Test with exactly 10 nodes (at threshold)
        runtime_10 = EnvelopeRouter()
        for i in range(10):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime_10.register_node(instance)

        repr_10 = repr(runtime_10)
        assert "nodes=[" in repr_10  # Full list format
        assert "<10 nodes>" not in repr_10

        # Test with exactly 11 nodes (above threshold)
        runtime_11 = EnvelopeRouter()
        for i in range(11):
            instance = NodeInstance(
                slug=f"node-{i}",
                node_type=sample_node_type,
                contract=mock_contract,
            )
            runtime_11.register_node(instance)

        repr_11 = repr(runtime_11)
        assert "<11 nodes>" in repr_11  # Abbreviated format
        assert "nodes=[" not in repr_11

    def test_repr_with_maximum_handler_types(self) -> None:
        """
        Test __repr__ with all available EnumHandlerType values registered.

        EXPECTED BEHAVIOR:
        - All 12 EnumHandlerType values can be registered
        - Since 12 > 10 threshold, shows '<12 handlers>'
        - No errors occur when registering all handler types
        """
        from unittest.mock import MagicMock

        from omnibase_core.enums.enum_handler_type import EnumHandlerType
        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()

        # Register ALL available handler types
        all_handler_types = list(EnumHandlerType)
        for handler_type in all_handler_types:
            handler = MagicMock()
            handler.handler_type = handler_type
            handler.execute = MagicMock()
            handler.describe = MagicMock(
                return_value={"name": f"handler_{handler_type.value}"}
            )
            runtime.register_handler(handler)

        # Verify all handlers were registered
        assert len(runtime._handlers) == len(all_handler_types)

        repr_str = repr(runtime)

        # Should show abbreviated count (12 > 10 threshold)
        expected_count = len(all_handler_types)
        assert f"<{expected_count} handlers>" in repr_str
        assert "handlers=[" not in repr_str


# =============================================================================
# TEST CLASS: Handler Execution Timeout Behavior
# =============================================================================


@pytest.mark.timeout(90)
@pytest.mark.unit
class TestEnvelopeRouterHandlerTimeout:
    """
    Tests for handler execution timeout behavior.

    The EnvelopeRouter.execute_with_handler() method calls handler.execute()
    directly WITHOUT built-in timeout handling. This is intentional - timeout
    handling is the CALLER'S responsibility.

    These tests document:
    1. Slow handlers still complete successfully (no internal timeout)
    2. Callers can use asyncio.wait_for() for timeout control
    3. asyncio.CancelledError propagates correctly (not caught/converted)

    This design allows callers to choose appropriate timeout policies for their
    use case rather than imposing a one-size-fits-all timeout.

    Note:
    - Extended timeout (90s) for tests involving intentional delays and timeouts
    """

    @pytest.mark.asyncio
    async def test_slow_handler_completes_successfully(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that slow handler still completes successfully.

        EXPECTED BEHAVIOR:
        - Handler that takes 100ms completes without issue
        - Response is returned correctly with expected payload
        - No internal timeout interrupts the execution
        """
        import asyncio

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        async def slow_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            await asyncio.sleep(0.1)  # 100ms delay - slow but acceptable
            return ModelOnexEnvelope.create_response(
                request=envelope,
                payload={"status": "slow_complete"},
                success=True,
            )

        slow_handler = MagicMock()
        slow_handler.handler_type = EnumHandlerType.HTTP
        slow_handler.execute = slow_execute  # Direct async function, not AsyncMock
        slow_handler.describe = MagicMock(return_value={"type": "slow"})

        runtime = EnvelopeRouter()
        runtime.register_handler(slow_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test",
            operation="SLOW_TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,
        )

        result = await runtime.execute_with_handler(envelope, instance)

        assert result.success is True
        assert result.payload.get("status") == "slow_complete"

    @pytest.mark.asyncio
    async def test_caller_can_timeout_with_wait_for(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that callers can use asyncio.wait_for for timeout control.

        EXPECTED BEHAVIOR:
        - Handler that would take 2s can be timed out by caller using asyncio.wait_for
        - asyncio.TimeoutError is raised when timeout (50ms) exceeded
        - This documents the RECOMMENDED timeout pattern for callers

        DESIGN RATIONALE:
        - EnvelopeRouter does NOT impose built-in timeouts
        - Timeout policy is the caller's responsibility
        - asyncio.wait_for() is the idiomatic Python approach
        """
        import asyncio

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        async def hanging_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            # Would hang for 2 seconds if not timed out
            await asyncio.sleep(2.0)
            return ModelOnexEnvelope.create_response(
                request=envelope,
                payload={},
                success=True,
            )

        hanging_handler = MagicMock()
        hanging_handler.handler_type = EnumHandlerType.HTTP
        hanging_handler.execute = hanging_execute  # Direct async function
        hanging_handler.describe = MagicMock(return_value={})

        runtime = EnvelopeRouter()
        runtime.register_handler(hanging_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test",
            operation="TIMEOUT_TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,
        )

        # Caller controls timeout with asyncio.wait_for - recommended pattern
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                runtime.execute_with_handler(envelope, instance),
                timeout=0.05,  # 50ms timeout - much less than 2s handler
            )

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that asyncio.CancelledError propagates correctly (not caught).

        EXPECTED BEHAVIOR:
        - When a task is cancelled during handler execution, CancelledError propagates
        - CancelledError is NOT caught and converted to error envelope
        - This is required for proper task cleanup semantics in asyncio

        DESIGN RATIONALE:
        - Catching CancelledError would break asyncio task cancellation semantics
        - The EnvelopeRouter explicitly re-raises CancelledError (see lines 742-744)
        - Callers must be able to cancel long-running operations gracefully
        """
        import asyncio

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        async def cancellable_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            # Will be cancelled before completion
            await asyncio.sleep(10.0)
            return ModelOnexEnvelope.create_response(
                request=envelope,
                payload={},
                success=True,
            )

        cancellable_handler = MagicMock()
        cancellable_handler.handler_type = EnumHandlerType.HTTP
        cancellable_handler.execute = cancellable_execute  # Direct async function
        cancellable_handler.describe = MagicMock(return_value={})

        runtime = EnvelopeRouter()
        runtime.register_handler(cancellable_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test",
            operation="CANCEL_TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,
        )

        # Create task and cancel it
        task = asyncio.create_task(runtime.execute_with_handler(envelope, instance))

        await asyncio.sleep(0.05)  # 50ms - let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_timeout_error_vs_handler_error_distinction(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test distinction between timeout errors and handler execution errors.

        EXPECTED BEHAVIOR:
        - Handler execution errors (RuntimeError, ValueError, etc.) return error envelope
        - Timeout errors (asyncio.TimeoutError from wait_for) propagate as exceptions
        - This is the correct asymmetry per the documented contract

        DESIGN RATIONALE:
        - Timeouts are caller-controlled and should raise exceptions
        - Handler bugs/failures are converted to error envelopes for observability
        - This allows correlation_id tracking for handler errors
        """
        import asyncio

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        # Handler that raises a regular exception (NOT timeout)
        async def error_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            raise RuntimeError("Simulated handler failure")

        error_handler = MagicMock()
        error_handler.handler_type = EnumHandlerType.HTTP
        error_handler.execute = error_execute
        error_handler.describe = MagicMock(return_value={})

        # Define slow handler for timeout test
        async def slow_execute(envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
            await asyncio.sleep(2.0)
            return ModelOnexEnvelope.create_response(
                request=envelope,
                payload={},
                success=True,
            )

        slow_handler = MagicMock()
        slow_handler.handler_type = EnumHandlerType.DATABASE  # Different type
        slow_handler.execute = slow_execute
        slow_handler.describe = MagicMock(return_value={})

        runtime = EnvelopeRouter()
        runtime.register_handler(error_handler)
        runtime.register_handler(slow_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # CRITICAL: freeze before execution
        runtime.freeze()

        envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test",
            operation="ERROR_TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.HTTP,
        )

        # Handler error returns error envelope (does NOT raise)
        result = await runtime.execute_with_handler(envelope, instance)
        assert result.success is False
        assert result.error is not None
        assert "Simulated handler failure" in result.error

        # Now test with a slow handler wrapped in wait_for - timeout RAISES
        timeout_envelope = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=default_version,
            correlation_id=uuid4(),
            source_node="test",
            operation="TIMEOUT_TEST",
            payload={},
            timestamp=datetime.now(UTC),
            handler_type=EnumHandlerType.DATABASE,
        )

        # Timeout from wait_for RAISES (does not return error envelope)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                runtime.execute_with_handler(timeout_envelope, instance),
                timeout=0.05,
            )


# =============================================================================
# TEST CLASS: Concurrency Stress Tests
# =============================================================================


@pytest.mark.slow
@pytest.mark.timeout(120)
@pytest.mark.unit
class TestEnvelopeRouterConcurrencyStress:
    """
    Stress tests for concurrent access patterns on EnvelopeRouter.

    These tests verify thread safety and race condition handling when:
    - Multiple threads call route_envelope after freeze
    - Multiple async tasks call execute_with_handler after freeze
    - Registration attempts occur during/after freeze

    Critical for production deployments where EnvelopeRouter may be accessed
    from multiple threads/tasks simultaneously.

    Note:
    - Marked as @slow due to 100-thread stress tests
    - Extended timeout (120s) for CI environments with resource constraints
    """

    def test_concurrent_route_envelope_after_freeze(
        self,
        mock_handler: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Stress test: 100 threads calling route_envelope after freeze.

        EXPECTED BEHAVIOR:
        - All 100 threads successfully route to correct handler
        - No race conditions or exceptions
        - Handler type matches for all threads
        """
        import threading

        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.freeze()

        results: list[dict] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def route_envelope_task(thread_id: int) -> None:
            try:
                envelope = ModelOnexEnvelope(
                    envelope_id=uuid4(),
                    envelope_version=default_version,
                    correlation_id=uuid4(),
                    source_node=f"thread-{thread_id}",
                    operation="STRESS_TEST",
                    payload={"thread_id": thread_id},
                    timestamp=datetime.now(UTC),
                    handler_type=mock_handler.handler_type,
                )
                result = runtime.route_envelope(envelope)
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Spawn 100 threads
        threads = [
            threading.Thread(target=route_envelope_task, args=(i,)) for i in range(100)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100
        assert all(r["handler"] is mock_handler for r in results)
        assert all(r["handler_type"] == mock_handler.handler_type for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_execute_with_handler_after_freeze(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Stress test: 50 concurrent async tasks calling execute_with_handler.

        EXPECTED BEHAVIOR:
        - All 50 tasks complete successfully
        - All responses are valid envelopes with is_response=True
        - Handler execute() called 50 times
        """
        import asyncio

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)
        runtime.freeze()

        async def execute_task(task_id: int) -> ModelOnexEnvelope:
            envelope = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=uuid4(),
                source_node=f"task-{task_id}",
                operation="ASYNC_STRESS_TEST",
                payload={"task_id": task_id},
                timestamp=datetime.now(UTC),
                handler_type=mock_handler.handler_type,
            )
            return await runtime.execute_with_handler(envelope, instance)

        # Run 50 concurrent tasks
        tasks = [execute_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # Verify all results are valid response envelopes
        valid_results = [r for r in results if isinstance(r, ModelOnexEnvelope)]
        assert len(valid_results) == 50
        assert all(r.is_response for r in valid_results)

        # Verify handler was called 50 times
        assert mock_handler.execute.call_count == 50

    def test_registration_during_freeze_attempt(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Edge case: Multiple threads attempting registration while freeze is called.

        EXPECTED BEHAVIOR:
        - Freeze wins and subsequent registrations fail with INVALID_STATE
        - Some registrations may succeed (before freeze completes)
        - Some registrations fail with INVALID_STATE (after freeze completes)
        - No race conditions or crashes
        - Router state is consistent after all threads complete
        """
        import threading
        import time

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        successful_registrations: list[str] = []
        invalid_state_errors: list[str] = []
        other_errors: list[Exception] = []
        lock = threading.Lock()

        # Event to synchronize thread start
        start_event = threading.Event()
        # Event to signal freeze has been called
        freeze_called = threading.Event()

        def register_node_task(node_id: int) -> None:
            # Wait for start signal to maximize concurrency
            start_event.wait()

            try:
                instance = NodeInstance(
                    slug=f"concurrent-node-{node_id}",
                    node_type=sample_node_type,
                    contract=mock_contract,
                )
                runtime.register_node(instance)
                with lock:
                    successful_registrations.append(f"concurrent-node-{node_id}")
            except ModelOnexError as e:
                with lock:
                    if e.error_code == EnumCoreErrorCode.INVALID_STATE:
                        invalid_state_errors.append(f"concurrent-node-{node_id}")
                    else:
                        other_errors.append(e)
            except Exception as e:
                with lock:
                    other_errors.append(e)

        def freeze_task() -> None:
            # Wait for start signal
            start_event.wait()
            # Small delay to let some registrations start
            time.sleep(0.001)
            runtime.freeze()
            freeze_called.set()

        # Create registration threads (20 threads trying to register)
        registration_threads = [
            threading.Thread(target=register_node_task, args=(i,)) for i in range(20)
        ]

        # Create freeze thread
        freeze_thread = threading.Thread(target=freeze_task)

        # Start all threads
        for t in registration_threads:
            t.start()
        freeze_thread.start()

        # Signal all threads to start simultaneously
        start_event.set()

        # Wait for all threads to complete
        freeze_thread.join()
        for t in registration_threads:
            t.join()

        # Verify no unexpected errors
        assert len(other_errors) == 0, f"Unexpected errors: {other_errors}"

        # Verify router is frozen
        assert runtime.is_frozen is True

        # Verify consistency: total should be 20 (either success or INVALID_STATE)
        total_outcomes = len(successful_registrations) + len(invalid_state_errors)
        assert total_outcomes == 20, (
            f"Expected 20 outcomes, got {total_outcomes} "
            f"(success: {len(successful_registrations)}, "
            f"invalid_state: {len(invalid_state_errors)})"
        )

        # Verify successful registrations are actually in the router
        for slug in successful_registrations:
            assert slug in runtime._nodes, f"Slug {slug} not found in router nodes"

        # Verify router node count matches successful registrations
        assert len(runtime._nodes) == len(successful_registrations)

    def test_concurrent_route_with_multiple_handler_types(
        self,
        mock_handler: MagicMock,
        mock_handler_database: MagicMock,
        mock_handler_kafka: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Stress test: Multiple threads routing to different handler types.

        EXPECTED BEHAVIOR:
        - Threads routing to HTTP get HTTP handler
        - Threads routing to DATABASE get DATABASE handler
        - Threads routing to KAFKA get KAFKA handler
        - No cross-contamination between handler types
        """
        import threading

        from omnibase_core.runtime import EnvelopeRouter

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)
        runtime.register_handler(mock_handler_database)
        runtime.register_handler(mock_handler_kafka)
        runtime.freeze()

        results_by_type: dict[EnumHandlerType, list[dict]] = {
            EnumHandlerType.HTTP: [],
            EnumHandlerType.DATABASE: [],
            EnumHandlerType.KAFKA: [],
        }
        errors: list[Exception] = []
        lock = threading.Lock()

        def route_to_handler_type(
            thread_id: int, handler_type: EnumHandlerType
        ) -> None:
            try:
                envelope = ModelOnexEnvelope(
                    envelope_id=uuid4(),
                    envelope_version=default_version,
                    correlation_id=uuid4(),
                    source_node=f"thread-{thread_id}",
                    operation="MULTI_HANDLER_STRESS",
                    payload={"thread_id": thread_id, "target": handler_type.value},
                    timestamp=datetime.now(UTC),
                    handler_type=handler_type,
                )
                result = runtime.route_envelope(envelope)
                with lock:
                    results_by_type[handler_type].append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Create 90 threads: 30 for each handler type
        threads = []
        for i in range(30):
            threads.append(
                threading.Thread(
                    target=route_to_handler_type,
                    args=(i, EnumHandlerType.HTTP),
                )
            )
            threads.append(
                threading.Thread(
                    target=route_to_handler_type,
                    args=(i + 30, EnumHandlerType.DATABASE),
                )
            )
            threads.append(
                threading.Thread(
                    target=route_to_handler_type,
                    args=(i + 60, EnumHandlerType.KAFKA),
                )
            )

        # Start and join all threads
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify correct counts per handler type
        assert len(results_by_type[EnumHandlerType.HTTP]) == 30
        assert len(results_by_type[EnumHandlerType.DATABASE]) == 30
        assert len(results_by_type[EnumHandlerType.KAFKA]) == 30

        # Verify each handler type got the correct handler (no cross-contamination)
        for result in results_by_type[EnumHandlerType.HTTP]:
            assert result["handler"] is mock_handler
            assert result["handler_type"] == EnumHandlerType.HTTP

        for result in results_by_type[EnumHandlerType.DATABASE]:
            assert result["handler"] is mock_handler_database
            assert result["handler_type"] == EnumHandlerType.DATABASE

        for result in results_by_type[EnumHandlerType.KAFKA]:
            assert result["handler"] is mock_handler_kafka
            assert result["handler_type"] == EnumHandlerType.KAFKA

    @pytest.mark.asyncio
    async def test_high_concurrency_async_execution(
        self,
        mock_handler: MagicMock,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        High concurrency test: 100 async tasks with varying delays.

        EXPECTED BEHAVIOR:
        - All 100 tasks complete regardless of execution order
        - Correlation IDs are preserved in responses
        - No deadlocks or hangs
        """
        import asyncio
        import random

        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()
        runtime.register_handler(mock_handler)

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)
        runtime.freeze()

        correlation_ids: list[tuple[int, uuid4]] = []

        async def execute_with_jitter(task_id: int) -> tuple[int, ModelOnexEnvelope]:
            # Add random jitter to simulate real-world conditions
            await asyncio.sleep(random.uniform(0, 0.01))

            corr_id = uuid4()
            correlation_ids.append((task_id, corr_id))

            envelope = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=corr_id,
                source_node=f"async-task-{task_id}",
                operation="HIGH_CONCURRENCY_TEST",
                payload={"task_id": task_id},
                timestamp=datetime.now(UTC),
                handler_type=mock_handler.handler_type,
            )
            result = await runtime.execute_with_handler(envelope, instance)
            return (task_id, result)

        # Run 100 concurrent tasks
        tasks = [execute_with_jitter(i) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions
        exceptions = [(i, r) for i, r in enumerate(results) if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Exceptions in tasks: {exceptions}"

        # Verify all results are tuples with valid envelopes
        assert len(results) == 100
        for task_id, result in results:
            assert isinstance(result, ModelOnexEnvelope)
            assert result.is_response is True

        # Verify handler call count
        assert mock_handler.execute.call_count == 100

    def test_concurrent_registration_prevents_corruption(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Stress test: Concurrent handler and node registration from multiple threads.

        This test validates that the threading.Lock in EnvelopeRouter prevents
        data corruption when multiple threads attempt registration concurrently.

        EXPECTED BEHAVIOR:
        - All registration attempts either succeed or fail with ModelOnexError
        - No data corruption (internal state remains consistent)
        - Registered handlers/nodes are actually present in the registries
        - Thread-local state is not corrupted by concurrent access

        Note:
            This tests that threading.Lock prevents data corruption, NOT that
            concurrent registration is semantically race-free. Duplicate key
            registration may raise errors (expected behavior for nodes), and
            handler registration with replace=True may have last-write-wins
            semantics. The key invariant is that no corruption occurs.

        Validates docstring claim in envelope_router.py line 156:
            "Safe concurrent registration from multiple threads (if needed)"
        """
        import threading

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # Track outcomes from concurrent registration
        handler_successes: list[EnumHandlerType] = []
        handler_errors: list[tuple[EnumHandlerType, Exception]] = []
        node_successes: list[str] = []
        node_errors: list[tuple[str, Exception]] = []
        lock = threading.Lock()

        # Event to synchronize thread start for maximum concurrency
        start_event = threading.Event()

        def register_handler_task(thread_id: int) -> None:
            """Register handlers with different handler_types concurrently."""
            start_event.wait()

            # Use different handler types for different threads to avoid
            # semantic conflicts while still testing lock protection
            handler_types = list(EnumHandlerType)
            handler_type = handler_types[thread_id % len(handler_types)]

            try:
                handler = MagicMock()
                handler.handler_type = handler_type
                handler.execute = MagicMock()
                handler.describe = MagicMock(
                    return_value={
                        "name": f"concurrent_handler_{thread_id}",
                        "version": ModelSemVer(major=1, minor=0, patch=0),
                    }
                )

                # Use replace=True to allow multiple registrations for same type
                # (this is the default, but explicit for clarity)
                runtime.register_handler(handler, replace=True)
                with lock:
                    handler_successes.append(handler_type)
            except ModelOnexError as e:
                with lock:
                    handler_errors.append((handler_type, e))
            except Exception as e:
                with lock:
                    handler_errors.append((handler_type, e))

        def register_node_task(thread_id: int) -> None:
            """Register nodes with unique slugs concurrently."""
            start_event.wait()

            # Each thread gets a unique slug to avoid DUPLICATE_REGISTRATION errors
            slug = f"concurrent-node-{thread_id}"

            try:
                instance = NodeInstance(
                    slug=slug,
                    node_type=sample_node_type,
                    contract=mock_contract,
                )
                runtime.register_node(instance)
                with lock:
                    node_successes.append(slug)
            except ModelOnexError as e:
                with lock:
                    node_errors.append((slug, e))
            except Exception as e:
                with lock:
                    node_errors.append((slug, e))

        # Create threads: 20 handler registrations + 20 node registrations
        handler_threads = [
            threading.Thread(target=register_handler_task, args=(i,)) for i in range(20)
        ]
        node_threads = [
            threading.Thread(target=register_node_task, args=(i,)) for i in range(20)
        ]

        # Start all threads
        all_threads = handler_threads + node_threads
        for t in all_threads:
            t.start()

        # Signal all threads to start simultaneously for maximum concurrency
        start_event.set()

        # Wait for all threads to complete
        for t in all_threads:
            t.join()

        # === VERIFICATION: No data corruption ===

        # 1. No unexpected errors (only ModelOnexError with expected codes is OK)
        unexpected_handler_errors = [
            (ht, e)
            for ht, e in handler_errors
            if not isinstance(e, ModelOnexError)
            or e.error_code
            not in (
                EnumCoreErrorCode.INVALID_STATE,
                EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )
        ]
        assert len(unexpected_handler_errors) == 0, (
            f"Unexpected handler errors: {unexpected_handler_errors}"
        )

        unexpected_node_errors = [
            (slug, e)
            for slug, e in node_errors
            if not isinstance(e, ModelOnexError)
            or e.error_code
            not in (
                EnumCoreErrorCode.INVALID_STATE,
                EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )
        ]
        assert len(unexpected_node_errors) == 0, (
            f"Unexpected node errors: {unexpected_node_errors}"
        )

        # 2. All successful node registrations are actually in the registry
        for slug in node_successes:
            assert slug in runtime._nodes, (
                f"Node {slug} reported success but not in registry"
            )

        # 3. Registry node count matches successful registrations
        # (since each thread has unique slug, no duplicates expected)
        assert len(runtime._nodes) == len(node_successes), (
            f"Node count mismatch: registry has {len(runtime._nodes)}, successes: {len(node_successes)}"
        )

        # 4. Handler registry is consistent (handlers may have been replaced,
        # but registry should contain valid handlers for each registered type)
        for handler_type in runtime._handlers:
            handler = runtime._handlers[handler_type]
            assert handler is not None, f"Handler for {handler_type} is None"
            assert hasattr(handler, "handler_type"), (
                f"Handler for {handler_type} missing handler_type"
            )

        # 5. All operations accounted for (success + expected errors = total attempts)
        total_handler_outcomes = len(handler_successes) + len(handler_errors)
        assert total_handler_outcomes == 20, (
            f"Handler outcomes: {total_handler_outcomes} != 20"
        )

        total_node_outcomes = len(node_successes) + len(node_errors)
        assert total_node_outcomes == 20, f"Node outcomes: {total_node_outcomes} != 20"

        # 6. Registry is not in corrupted state (can still perform operations)
        # This verifies internal data structures weren't corrupted by concurrent access
        assert isinstance(runtime._handlers, dict), "Handler registry corrupted"
        assert isinstance(runtime._nodes, dict), "Node registry corrupted"
        assert isinstance(runtime._frozen, bool), "Frozen flag corrupted"

    def test_concurrent_registration_with_duplicate_slugs(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: MagicMock,
    ) -> None:
        """
        Stress test: Multiple threads trying to register nodes with SAME slug.

        This tests that the lock prevents race conditions where two threads
        both pass the "slug not in registry" check before either inserts,
        potentially causing data loss or inconsistent state.

        EXPECTED BEHAVIOR:
        - Exactly one thread succeeds in registering the slug
        - All other threads receive DUPLICATE_REGISTRATION error
        - No data corruption or lost registrations
        - The successfully registered node is the one in the registry
        """
        import threading

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import EnvelopeRouter, NodeInstance

        runtime = EnvelopeRouter()

        # All threads try to register the SAME slug
        target_slug = "contested-node-slug"

        successes: list[int] = []  # Thread IDs that succeeded
        duplicate_errors: list[int] = []  # Thread IDs that got DUPLICATE_REGISTRATION
        other_errors: list[tuple[int, Exception]] = []
        lock = threading.Lock()

        # Event to synchronize thread start
        start_event = threading.Event()

        def register_same_slug_task(thread_id: int) -> None:
            """All threads try to register the same slug."""
            start_event.wait()

            try:
                instance = NodeInstance(
                    slug=target_slug,
                    node_type=sample_node_type,
                    contract=mock_contract,
                )
                runtime.register_node(instance)
                with lock:
                    successes.append(thread_id)
            except ModelOnexError as e:
                with lock:
                    if e.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION:
                        duplicate_errors.append(thread_id)
                    else:
                        other_errors.append((thread_id, e))
            except Exception as e:
                with lock:
                    other_errors.append((thread_id, e))

        # Create 50 threads all trying to register the same slug
        threads = [
            threading.Thread(target=register_same_slug_task, args=(i,))
            for i in range(50)
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Signal all threads to start simultaneously
        start_event.set()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # === VERIFICATION ===

        # 1. No unexpected errors
        assert len(other_errors) == 0, f"Unexpected errors: {other_errors}"

        # 2. Exactly one thread succeeded
        assert len(successes) == 1, (
            f"Expected exactly 1 success, got {len(successes)}: {successes}"
        )

        # 3. All other threads got DUPLICATE_REGISTRATION
        assert len(duplicate_errors) == 49, (
            f"Expected 49 duplicates, got {len(duplicate_errors)}"
        )

        # 4. Total outcomes = 50
        assert len(successes) + len(duplicate_errors) == 50

        # 5. The slug is in the registry exactly once
        assert target_slug in runtime._nodes
        assert len(runtime._nodes) == 1
