#!/usr/bin/env python3
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

import pytest

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


# =============================================================================
# TEST CLASS: Execute With Handler
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterExecuteWithHandler:
    """Tests for EnvelopeRouter execute_with_handler() method."""

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

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

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

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

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


@pytest.mark.unit
class TestEnvelopeRouterEdgeCases:
    """Tests for EnvelopeRouter edge cases and error conditions."""

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

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

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

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        runtime.register_node(instance)

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

        repr_str = repr(runtime)

        assert "EnvelopeRouter" in repr_str
        # All handler types should be visible
        assert mock_handler.handler_type.value in repr_str.lower()
        assert mock_handler_database.handler_type.value in repr_str.lower()
        assert mock_handler_kafka.handler_type.value in repr_str.lower()


# =============================================================================
# TEST CLASS: Integration Patterns
# =============================================================================


@pytest.mark.unit
class TestEnvelopeRouterIntegrationPatterns:
    """Tests for common EnvelopeRouter usage patterns."""

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

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

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

        # All nodes should be registered
        assert len(runtime._nodes) == len(node_types)  # Should be 4

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
