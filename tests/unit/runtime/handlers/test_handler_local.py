"""
Tests for HandlerLocal - echo handler for development and testing.

This module tests the HandlerLocal implementation including:
- Protocol compliance with ProtocolHandler
- Handler type returns EnumHandlerType.LOCAL (not a string)
- Warning logged on initialization
- Health check behavior
- describe() returns correct metadata
- Echo operation behavior
- Transform operation behavior
- Error operation behavior
"""

import logging
from typing import Any

import pytest

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler
from omnibase_core.runtime.handlers.handler_local import HandlerLocal


@pytest.mark.unit
class TestHandlerLocalProtocolCompliance:
    """Tests for HandlerLocal protocol compliance."""

    def test_handler_implements_protocol(self) -> None:
        """Test that HandlerLocal implements ProtocolHandler protocol."""
        handler = HandlerLocal()
        # ProtocolHandler is runtime_checkable, so isinstance works
        assert isinstance(handler, ProtocolHandler)

    def test_handler_has_handler_type_property(self) -> None:
        """Test that handler has handler_type property."""
        handler = HandlerLocal()
        assert hasattr(handler, "handler_type")
        # Property should be callable without arguments
        _ = handler.handler_type

    def test_handler_has_execute_method(self) -> None:
        """Test that handler has execute method."""
        handler = HandlerLocal()
        assert hasattr(handler, "execute")
        assert callable(handler.execute)

    def test_handler_has_describe_method(self) -> None:
        """Test that handler has describe method."""
        handler = HandlerLocal()
        assert hasattr(handler, "describe")
        assert callable(handler.describe)


@pytest.mark.unit
class TestHandlerLocalType:
    """Tests for HandlerLocal handler_type property."""

    def test_handler_type_returns_enum_not_string(self) -> None:
        """Test that handler_type returns EnumHandlerType.LOCAL, not a string."""
        handler = HandlerLocal()
        handler_type = handler.handler_type

        # Must be the enum value, not a string
        assert handler_type is EnumHandlerType.LOCAL
        assert isinstance(handler_type, EnumHandlerType)

        # Verify it's the correct enum value
        assert handler_type == EnumHandlerType.LOCAL
        assert handler_type.value == "local"

    def test_handler_type_is_property(self) -> None:
        """Test that handler_type is accessed as a property, not a method."""
        handler = HandlerLocal()

        # Access as property (no parentheses)
        handler_type = handler.handler_type
        assert handler_type == EnumHandlerType.LOCAL


@pytest.mark.unit
class TestHandlerLocalInitialization:
    """Tests for HandlerLocal initialization behavior."""

    def test_warning_logged_on_initialization(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a warning is logged when HandlerLocal is initialized."""
        with caplog.at_level(logging.WARNING, logger="omnibase"):
            _ = HandlerLocal()

        # Check that a warning was logged
        assert len(caplog.records) >= 1

        # Find the warning from HandlerLocal initialization
        warning_found = False
        for record in caplog.records:
            if (
                "HandlerLocal" in record.message
                and "dev/test" in record.message.lower()
            ):
                warning_found = True
                assert record.levelno == logging.WARNING
                break

        assert warning_found, (
            "Expected warning about dev/test only usage not found in logs"
        )

    def test_handler_can_be_instantiated_multiple_times(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that handler can be instantiated multiple times."""
        with caplog.at_level(logging.WARNING, logger="omnibase"):
            handler1 = HandlerLocal()
            handler2 = HandlerLocal()

        # Both should be valid handlers
        assert isinstance(handler1, ProtocolHandler)
        assert isinstance(handler2, ProtocolHandler)

        # They should be different instances
        assert handler1 is not handler2


@pytest.mark.unit
class TestHandlerLocalHealthCheck:
    """Tests for HandlerLocal health_check method."""

    def test_health_check_returns_dict(self) -> None:
        """Test that health_check returns a dictionary."""
        handler = HandlerLocal()
        result = handler.health_check()

        assert isinstance(result, dict)

    def test_health_check_contains_dev_test_only_flag(self) -> None:
        """Test that health_check returns dev_test_only: True."""
        handler = HandlerLocal()
        result = handler.health_check()

        assert "dev_test_only" in result
        assert result["dev_test_only"] is True

    def test_health_check_contains_status_healthy(self) -> None:
        """Test that health_check returns status: healthy."""
        handler = HandlerLocal()
        result = handler.health_check()

        assert "status" in result
        assert result["status"] == "healthy"


@pytest.mark.unit
class TestHandlerLocalDescribe:
    """Tests for HandlerLocal describe method."""

    def test_describe_returns_typed_dict(self) -> None:
        """Test that describe returns TypedDictHandlerMetadata structure."""
        handler = HandlerLocal()
        metadata = handler.describe()

        # Required fields
        assert "name" in metadata
        assert "version" in metadata

        # Values should be correct types
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["version"], ModelSemVer)

    def test_describe_returns_correct_name(self) -> None:
        """Test that describe returns correct handler name."""
        handler = HandlerLocal()
        metadata = handler.describe()

        assert metadata["name"] == "handler_local"

    def test_describe_returns_correct_version(self) -> None:
        """Test that describe returns correct version."""
        handler = HandlerLocal()
        metadata = handler.describe()

        version = metadata["version"]
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_describe_includes_description(self) -> None:
        """Test that describe includes a description with dev/test warning."""
        handler = HandlerLocal()
        metadata = handler.describe()

        assert "description" in metadata
        description = metadata["description"]
        assert isinstance(description, str)
        assert "dev/test" in description.lower()
        assert "not for production" in description.lower()

    def test_describe_includes_capabilities(self) -> None:
        """Test that describe includes capabilities list."""
        handler = HandlerLocal()
        metadata = handler.describe()

        assert "capabilities" in metadata
        capabilities = metadata["capabilities"]
        assert isinstance(capabilities, list)
        assert "echo" in capabilities
        assert "transform" in capabilities
        assert "error" in capabilities


@pytest.mark.unit
class TestHandlerLocalEchoOperation:
    """Tests for HandlerLocal echo operation."""

    @pytest.mark.asyncio
    async def test_echo_returns_payload_unchanged(self) -> None:
        """Test that echo operation returns the input payload unchanged."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="echo",
            payload={"message": "hello", "count": 42},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload == {"message": "hello", "count": 42}

    @pytest.mark.asyncio
    async def test_echo_is_case_insensitive(self) -> None:
        """Test that echo operation is case-insensitive."""
        handler = HandlerLocal()

        for operation in ["echo", "ECHO", "Echo", "eCHo"]:
            request = ModelOnexEnvelope.create_request(
                operation=operation,
                payload={"test": "data"},
                source_node="test_client",
            )

            response = await handler.execute(request)
            assert response.success is True
            assert response.payload == {"test": "data"}

    @pytest.mark.asyncio
    async def test_echo_with_empty_payload(self) -> None:
        """Test that echo operation handles empty payload."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="echo",
            payload={},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload == {}

    @pytest.mark.asyncio
    async def test_echo_with_nested_payload(self) -> None:
        """Test that echo operation handles nested payload."""
        handler = HandlerLocal()

        nested_payload: dict[str, Any] = {
            "user": {
                "name": "Alice",
                "settings": {"theme": "dark"},
            },
            "items": [1, 2, 3],
        }

        request = ModelOnexEnvelope.create_request(
            operation="echo",
            payload=nested_payload,
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload == nested_payload

    @pytest.mark.asyncio
    async def test_echo_preserves_causation_chain(self) -> None:
        """Test that echo response has correct causation chain."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="echo",
            payload={"data": "test"},
            source_node="test_client",
        )

        response = await handler.execute(request)

        # Causation chain should be preserved
        assert response.correlation_id == request.correlation_id
        assert response.causation_id == request.envelope_id
        assert response.is_response is True


@pytest.mark.unit
class TestHandlerLocalTransformOperation:
    """Tests for HandlerLocal transform operation."""

    @pytest.mark.asyncio
    async def test_transform_uppercases_strings(self) -> None:
        """Test that transform operation uppercases string values."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={"text": "hello", "name": "world"},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload["text"] == "HELLO"
        assert response.payload["name"] == "WORLD"

    @pytest.mark.asyncio
    async def test_transform_doubles_integers(self) -> None:
        """Test that transform operation doubles integer values."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={"count": 5, "value": 100},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload["count"] == 10
        assert response.payload["value"] == 200

    @pytest.mark.asyncio
    async def test_transform_doubles_floats(self) -> None:
        """Test that transform operation doubles float values."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={"price": 3.14, "rate": 0.5},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload["price"] == 6.28
        assert response.payload["rate"] == 1.0

    @pytest.mark.asyncio
    async def test_transform_passes_through_other_types(self) -> None:
        """Test that transform operation passes through non-string/number types."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={
                "flag": True,
                "items": [1, 2, 3],
                "data": None,
            },
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload["flag"] is True
        assert response.payload["items"] == [1, 2, 3]
        assert response.payload["data"] is None

    @pytest.mark.asyncio
    async def test_transform_does_not_double_booleans(self) -> None:
        """Test that transform operation does not double boolean values."""
        handler = HandlerLocal()

        # In Python, bool is a subclass of int, so we need to handle this
        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={"flag": True, "other": False},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        # Booleans should pass through unchanged, not be doubled
        assert response.payload["flag"] is True
        assert response.payload["other"] is False

    @pytest.mark.asyncio
    async def test_transform_mixed_payload(self) -> None:
        """Test that transform operation handles mixed payload types."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={
                "text": "hello",
                "count": 10,
                "price": 2.5,
                "active": True,
            },
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is True
        assert response.payload["text"] == "HELLO"
        assert response.payload["count"] == 20
        assert response.payload["price"] == 5.0
        assert response.payload["active"] is True


@pytest.mark.unit
class TestHandlerLocalErrorOperation:
    """Tests for HandlerLocal error operation."""

    @pytest.mark.asyncio
    async def test_error_returns_error_envelope(self) -> None:
        """Test that error operation returns an error envelope."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="error",
            payload={},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is False
        assert response.is_response is True
        assert response.error is not None
        assert len(response.error) > 0

    @pytest.mark.asyncio
    async def test_error_uses_default_message(self) -> None:
        """Test that error operation uses default message when not provided."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="error",
            payload={},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is False
        assert "Deliberate error for testing" in response.error

    @pytest.mark.asyncio
    async def test_error_uses_custom_message(self) -> None:
        """Test that error operation uses custom message when provided."""
        handler = HandlerLocal()

        custom_error = "Custom error message for testing"
        request = ModelOnexEnvelope.create_request(
            operation="error",
            payload={"error_message": custom_error},
            source_node="test_client",
        )

        response = await handler.execute(request)

        assert response.success is False
        assert response.error == custom_error

    @pytest.mark.asyncio
    async def test_error_preserves_causation_chain(self) -> None:
        """Test that error response has correct causation chain."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="error",
            payload={},
            source_node="test_client",
        )

        response = await handler.execute(request)

        # Causation chain should be preserved even for errors
        assert response.correlation_id == request.correlation_id
        assert response.causation_id == request.envelope_id
        assert response.is_response is True


@pytest.mark.unit
class TestHandlerLocalUnknownOperation:
    """Tests for HandlerLocal behavior with unknown operations."""

    @pytest.mark.asyncio
    async def test_unknown_operation_defaults_to_echo(self) -> None:
        """Test that unknown operations default to echo behavior."""
        handler = HandlerLocal()

        request = ModelOnexEnvelope.create_request(
            operation="unknown_operation",
            payload={"data": "test"},
            source_node="test_client",
        )

        response = await handler.execute(request)

        # Should succeed with echo behavior
        assert response.success is True
        assert response.payload == {"data": "test"}

    @pytest.mark.asyncio
    async def test_custom_operation_defaults_to_echo(self) -> None:
        """Test that custom operations default to echo behavior."""
        handler = HandlerLocal()

        for operation in ["GET_DATA", "PROCESS", "my_custom_op"]:
            request = ModelOnexEnvelope.create_request(
                operation=operation,
                payload={"key": "value"},
                source_node="test_client",
            )

            response = await handler.execute(request)

            assert response.success is True
            assert response.payload == {"key": "value"}
