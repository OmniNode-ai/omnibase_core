"""Tests for ModelRegistryError."""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_registry_error_code import EnumRegistryErrorCode
from omnibase_core.models.common.model_registry_error import ModelRegistryError


class TestModelRegistryError:
    """Tests for ModelRegistryError model."""

    def test_initialization_minimal(self):
        """Test error initialization with minimal fields."""
        error = ModelRegistryError(
            message="Tool not found",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
        )

        assert error.message == "Tool not found"
        assert error.error_code == EnumRegistryErrorCode.TOOL_NOT_FOUND
        assert error.status == EnumOnexStatus.ERROR

    def test_initialization_with_context(self):
        """Test error initialization with context."""
        error = ModelRegistryError(
            message="Tool registration failed",
            error_code=EnumRegistryErrorCode.DUPLICATE_TOOL,
            tool_name="test_tool",
            reason="duplicate_key",
        )

        assert error.message == "Tool registration failed"
        assert error.error_code == EnumRegistryErrorCode.DUPLICATE_TOOL

    def test_default_status_is_error(self):
        """Test default status is ERROR."""
        error = ModelRegistryError(
            message="Test",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
        )
        assert error.status == EnumOnexStatus.ERROR

    def test_custom_status(self):
        """Test custom status override."""
        error = ModelRegistryError(
            message="Test",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
            status=EnumOnexStatus.WARNING,
        )
        assert error.status == EnumOnexStatus.WARNING

    def test_tool_not_found_error(self):
        """Test tool not found error."""
        error = ModelRegistryError(
            message="Tool 'my_tool' not found in registry",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
            tool_name="my_tool",
            registry_type="ToolRegistry",
        )

        assert "not found" in error.message
        assert error.error_code == EnumRegistryErrorCode.TOOL_NOT_FOUND

    def test_registry_unavailable_error(self):
        """Test registry unavailable error."""
        error = ModelRegistryError(
            message="Registry service unavailable",
            error_code=EnumRegistryErrorCode.REGISTRY_UNAVAILABLE,
            service_name="tool_registry",
            reason="connection_timeout",
        )

        assert error.error_code == EnumRegistryErrorCode.REGISTRY_UNAVAILABLE

    def test_duplicate_tool_error(self):
        """Test duplicate tool error."""
        error = ModelRegistryError(
            message="Tool already registered",
            error_code=EnumRegistryErrorCode.DUPLICATE_TOOL,
            tool_name="existing_tool",
        )

        assert error.error_code == EnumRegistryErrorCode.DUPLICATE_TOOL

    def test_inherits_from_onex_error(self):
        """Test ModelRegistryError inherits from ModelOnexError."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = ModelRegistryError(
            message="Test",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
        )

        assert isinstance(error, ModelOnexError)

    def test_correlation_id_tracking(self):
        """Test correlation ID can be passed in context."""
        corr_id = uuid4()
        error = ModelRegistryError(
            message="Test",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
            correlation_id=corr_id,
        )

        # correlation_id should be in the model (inherited from ModelOnexError)
        assert hasattr(error, "correlation_id")

    def test_context_kwargs(self):
        """Test additional context via kwargs."""
        error = ModelRegistryError(
            message="Complex error",
            error_code=EnumRegistryErrorCode.INVALID_MODE,
            tool_name="complex_tool",
            mode="invalid_mode",
            validation_errors=["missing_field", "invalid_type"],
            attempted_at="2025-05-25T10:00:00Z",
        )

        assert error.message == "Complex error"

    def test_error_code_required(self):
        """Test error_code is required."""
        with pytest.raises(Exception):  # ValidationError
            ModelRegistryError(message="Test")  # type: ignore[call-arg]

    def test_message_required(self):
        """Test message is required."""
        with pytest.raises(Exception):  # ValidationError or TypeError
            ModelRegistryError(  # type: ignore[call-arg]
                error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND
            )

    def test_serialization(self):
        """Test error can be serialized."""
        error = ModelRegistryError(
            message="Serialization test",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
            tool_name="test_tool",
        )

        data = error.model_dump()

        assert data["message"] == "Serialization test"
        assert "error_code" in data

    def test_multiple_errors_independent(self):
        """Test multiple errors are independent."""
        error1 = ModelRegistryError(
            message="Error 1",
            error_code=EnumRegistryErrorCode.TOOL_NOT_FOUND,
        )
        error2 = ModelRegistryError(
            message="Error 2",
            error_code=EnumRegistryErrorCode.DUPLICATE_TOOL,
        )

        assert error1.message != error2.message
        assert error1.error_code != error2.error_code

    def test_error_code_validation(self):
        """Test error codes from EnumRegistryErrorCode."""
        # Test each error code can be used
        for error_code in [
            EnumRegistryErrorCode.TOOL_NOT_FOUND,
            EnumRegistryErrorCode.DUPLICATE_TOOL,
            EnumRegistryErrorCode.INVALID_MODE,
            EnumRegistryErrorCode.REGISTRY_UNAVAILABLE,
        ]:
            error = ModelRegistryError(
                message=f"Test for {error_code}",
                error_code=error_code,
            )
            assert error.error_code == error_code
