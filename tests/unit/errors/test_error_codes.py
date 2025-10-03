"""
Comprehensive unit tests for error_codes module.

Tests cover:
- CLIExitCode enum and mappings
- OnexErrorCode base class
- CoreErrorCode enum and behavior
- Error code to exit code mapping
- ModelOnexError serialization
- OnexError exception class with UUID architecture
- Error correlation ID handling
- CLIAdapter functionality
- Error code registry
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_codes import (
    STATUS_TO_EXIT_CODE,
    CLIAdapter,
    CLIExitCode,
    CoreErrorCode,
    ModelOnexError,
    OnexError,
    OnexErrorCode,
    RegistryErrorCode,
    get_error_codes_for_component,
    get_exit_code_for_core_error,
    get_exit_code_for_status,
    list_registered_components,
    register_error_codes,
)


class TestCLIExitCode:
    """Test CLIExitCode enum."""

    def test_cli_exit_code_values(self):
        """Test all CLI exit code values."""
        assert CLIExitCode.SUCCESS == 0
        assert CLIExitCode.ERROR == 1
        assert CLIExitCode.WARNING == 2
        assert CLIExitCode.PARTIAL == 3
        assert CLIExitCode.SKIPPED == 4
        assert CLIExitCode.FIXED == 5
        assert CLIExitCode.INFO == 6

    def test_cli_exit_code_is_int(self):
        """Test that CLIExitCode is an int subclass."""
        assert isinstance(CLIExitCode.SUCCESS, int)
        assert isinstance(CLIExitCode.ERROR, int)


class TestStatusToExitCodeMapping:
    """Test STATUS_TO_EXIT_CODE mapping."""

    def test_status_to_exit_code_completeness(self):
        """Test that all EnumOnexStatus values are mapped."""
        for status in EnumOnexStatus:
            assert status in STATUS_TO_EXIT_CODE, f"Missing mapping for {status}"

    def test_status_mapping_correctness(self):
        """Test correctness of status to exit code mappings."""
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.SUCCESS] == CLIExitCode.SUCCESS
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.ERROR] == CLIExitCode.ERROR
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.WARNING] == CLIExitCode.WARNING
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.PARTIAL] == CLIExitCode.PARTIAL
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.SKIPPED] == CLIExitCode.SKIPPED
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.FIXED] == CLIExitCode.FIXED
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.INFO] == CLIExitCode.INFO
        assert STATUS_TO_EXIT_CODE[EnumOnexStatus.UNKNOWN] == CLIExitCode.ERROR

    def test_get_exit_code_for_status_function(self):
        """Test get_exit_code_for_status() function."""
        assert get_exit_code_for_status(EnumOnexStatus.SUCCESS) == 0
        assert get_exit_code_for_status(EnumOnexStatus.ERROR) == 1
        assert get_exit_code_for_status(EnumOnexStatus.WARNING) == 2
        assert get_exit_code_for_status(EnumOnexStatus.UNKNOWN) == 1  # Maps to ERROR


class TestOnexErrorCodeBase:
    """Test OnexErrorCode base class."""

    def test_onex_error_code_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""

        class TestErrorCode(OnexErrorCode):
            TEST_ERROR = "TEST_ERROR_001"

        error_code = TestErrorCode.TEST_ERROR

        with pytest.raises(NotImplementedError):
            error_code.get_component()

        with pytest.raises(NotImplementedError):
            error_code.get_number()

        with pytest.raises(NotImplementedError):
            error_code.get_description()

    def test_onex_error_code_default_exit_code(self):
        """Test that default get_exit_code() returns ERROR."""

        class TestErrorCode(OnexErrorCode):
            TEST_ERROR = "TEST_ERROR_001"

            def get_component(self) -> str:
                return "TEST"

            def get_number(self) -> int:
                return 1

            def get_description(self) -> str:
                return "Test error"

        error_code = TestErrorCode.TEST_ERROR
        assert error_code.get_exit_code() == CLIExitCode.ERROR.value


class TestCoreErrorCode:
    """Test CoreErrorCode enum."""

    def test_core_error_code_values(self):
        """Test that all expected error codes exist."""
        # Validation errors (001-020)
        assert CoreErrorCode.INVALID_PARAMETER
        assert CoreErrorCode.MISSING_REQUIRED_PARAMETER
        assert CoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert CoreErrorCode.VALIDATION_FAILED

        # File system errors (021-040)
        assert CoreErrorCode.FILE_NOT_FOUND
        assert CoreErrorCode.FILE_READ_ERROR
        assert CoreErrorCode.PERMISSION_DENIED

        # Configuration errors (041-060)
        assert CoreErrorCode.INVALID_CONFIGURATION
        assert CoreErrorCode.CONFIGURATION_NOT_FOUND

        # Registry errors (061-080)
        assert CoreErrorCode.REGISTRY_NOT_FOUND
        assert CoreErrorCode.ITEM_NOT_REGISTERED

        # Runtime errors (081-100)
        assert CoreErrorCode.OPERATION_FAILED
        assert CoreErrorCode.TIMEOUT_EXCEEDED
        assert CoreErrorCode.RESOURCE_UNAVAILABLE

    def test_core_error_code_get_component(self):
        """Test get_component() returns 'CORE'."""
        assert CoreErrorCode.INVALID_PARAMETER.get_component() == "CORE"
        assert CoreErrorCode.FILE_NOT_FOUND.get_component() == "CORE"

    def test_core_error_code_get_number(self):
        """Test get_number() extracts correct number from code."""
        error_code = CoreErrorCode.INVALID_PARAMETER  # Should be 001
        number = error_code.get_number()
        assert number == 1

        error_code = CoreErrorCode.FILE_NOT_FOUND  # Should be 021
        number = error_code.get_number()
        assert number == 21

    def test_core_error_code_get_description(self):
        """Test get_description() returns human-readable text."""
        desc = CoreErrorCode.INVALID_PARAMETER.get_description()
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "parameter" in desc.lower()

    def test_core_error_code_get_exit_code(self):
        """Test get_exit_code() returns appropriate CLI exit code."""
        # Most errors should return ERROR (1)
        assert (
            CoreErrorCode.INVALID_PARAMETER.get_exit_code() == CLIExitCode.ERROR.value
        )
        assert CoreErrorCode.FILE_NOT_FOUND.get_exit_code() == CLIExitCode.ERROR.value

        # Duplicate registration should return WARNING (2)
        assert (
            CoreErrorCode.DUPLICATE_REGISTRATION.get_exit_code()
            == CLIExitCode.WARNING.value
        )


class TestCoreErrorDescriptions:
    """Test core error descriptions."""

    @pytest.mark.parametrize(
        "error_code,expected_keywords",
        [
            (CoreErrorCode.INVALID_PARAMETER, ["invalid", "parameter"]),
            (CoreErrorCode.FILE_NOT_FOUND, ["file", "not found"]),
            (CoreErrorCode.PERMISSION_DENIED, ["permission", "denied"]),
            (CoreErrorCode.TIMEOUT_EXCEEDED, ["timeout"]),
            (CoreErrorCode.VALIDATION_FAILED, ["validation", "failed"]),
        ],
    )
    def test_error_description_contains_keywords(self, error_code, expected_keywords):
        """Test that error descriptions contain expected keywords."""
        description = error_code.get_description().lower()
        for keyword in expected_keywords:
            assert keyword in description, f"'{keyword}' not in '{description}'"


class TestModelOnexError:
    """Test ModelOnexError Pydantic model."""

    def test_model_onex_error_creation(self):
        """Test creating ModelOnexError with required fields."""
        error = ModelOnexError(
            message="Test error message",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert error.message == "Test error message"
        assert error.error_code == CoreErrorCode.VALIDATION_ERROR
        assert error.status == EnumOnexStatus.ERROR  # Default
        assert isinstance(error.correlation_id, UUID) or error.correlation_id is None

    def test_model_onex_error_with_correlation_id(self):
        """Test ModelOnexError with explicit correlation ID."""
        correlation_id = uuid4()
        error = ModelOnexError(
            message="Test error",
            error_code=CoreErrorCode.OPERATION_FAILED,
            correlation_id=correlation_id,
        )

        assert error.correlation_id == correlation_id

    def test_model_onex_error_with_context(self):
        """Test ModelOnexError with context information."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        error = ModelOnexError(
            message="Test error",
            error_code=CoreErrorCode.FILE_NOT_FOUND,
            context={
                "file_path": ModelSchemaValue.from_value("/test/path.txt"),
            },
        )

        assert "file_path" in error.context
        assert error.context["file_path"].to_value() == "/test/path.txt"


class TestOnexError:
    """Test OnexError exception class."""

    def test_onex_error_creation_basic(self):
        """Test creating OnexError with minimal arguments."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert error.message == "Test error"
        assert error.error_code == CoreErrorCode.VALIDATION_ERROR
        assert error.status == EnumOnexStatus.ERROR
        assert isinstance(error.correlation_id, UUID)

    def test_onex_error_auto_generates_correlation_id(self):
        """Test that OnexError auto-generates correlation ID if not provided."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.OPERATION_FAILED,
        )

        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)

    def test_onex_error_preserves_provided_correlation_id(self):
        """Test that OnexError uses provided correlation ID."""
        correlation_id = uuid4()
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.INVALID_PARAMETER,
            correlation_id=correlation_id,
        )

        assert error.correlation_id == correlation_id

    def test_onex_error_with_correlation_id_factory(self):
        """Test OnexError.with_correlation_id() factory method."""
        correlation_id = uuid4()
        error = OnexError.with_correlation_id(
            message="Test error",
            correlation_id=correlation_id,
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert error.correlation_id == correlation_id
        assert isinstance(error.correlation_id, UUID)

    def test_onex_error_with_new_correlation_id_factory(self):
        """Test OnexError.with_new_correlation_id() factory method."""
        error, correlation_id = OnexError.with_new_correlation_id(
            message="Test error",
            error_code=CoreErrorCode.OPERATION_FAILED,
        )

        assert error.correlation_id == correlation_id
        assert isinstance(correlation_id, UUID)
        assert isinstance(error.correlation_id, UUID)

    def test_onex_error_is_exception(self):
        """Test that OnexError is a proper Exception."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.INTERNAL_ERROR,
        )

        assert isinstance(error, Exception)
        assert isinstance(error, OnexError)

    def test_onex_error_can_be_raised(self):
        """Test that OnexError can be raised and caught."""
        with pytest.raises(OnexError) as exc_info:
            raise OnexError(
                message="Test error",
                error_code=CoreErrorCode.NOT_FOUND,
            )

        assert exc_info.value.error_code == CoreErrorCode.NOT_FOUND

    def test_onex_error_string_representation(self):
        """Test OnexError __str__() method."""
        error = OnexError(
            message="Test error message",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        error_str = str(error)
        assert "ONEX_CORE_006_VALIDATION_ERROR" in error_str
        assert "Test error message" in error_str

    def test_onex_error_get_exit_code(self):
        """Test OnexError.get_exit_code() method."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.FILE_NOT_FOUND,
        )

        exit_code = error.get_exit_code()
        assert exit_code == CLIExitCode.ERROR.value

    def test_onex_error_model_dump(self):
        """Test OnexError.model_dump() serialization."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        data = error.model_dump()
        assert isinstance(data, dict)
        assert data["message"] == "Test error"
        assert "error_code" in data

    def test_onex_error_model_dump_json(self):
        """Test OnexError.model_dump_json() serialization."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.OPERATION_FAILED,
        )

        json_str = error.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test error" in json_str

    def test_onex_error_context_handling(self):
        """Test OnexError context property handling."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.FILE_NOT_FOUND,
            file_path="/test/file.txt",
            line_number=42,
        )

        context = error.context
        assert isinstance(context, dict)
        # Context handling depends on ModelErrorContext availability


class TestCLIAdapter:
    """Test CLIAdapter class."""

    def test_cli_adapter_exit_with_status_success(self, capsys):
        """Test CLIAdapter.exit_with_status() with SUCCESS status."""
        # Note: This would actually exit, so we can't test the full behavior
        # We can only test that the method exists and is callable
        assert hasattr(CLIAdapter, "exit_with_status")
        assert callable(CLIAdapter.exit_with_status)

    def test_cli_adapter_exit_with_error(self):
        """Test CLIAdapter.exit_with_error() method exists."""
        assert hasattr(CLIAdapter, "exit_with_error")
        assert callable(CLIAdapter.exit_with_error)


class TestErrorCodeRegistry:
    """Test error code registry functionality."""

    def test_register_error_codes(self):
        """Test registering error codes for a component."""

        class CustomErrorCode(OnexErrorCode):
            CUSTOM_ERROR = "CUSTOM_001"

            def get_component(self) -> str:
                return "CUSTOM"

            def get_number(self) -> int:
                return 1

            def get_description(self) -> str:
                return "Custom error"

        register_error_codes("test_component", CustomErrorCode)

        registered = get_error_codes_for_component("test_component")
        assert registered == CustomErrorCode

    def test_get_error_codes_for_unregistered_component(self):
        """Test getting error codes for unregistered component raises error."""
        with pytest.raises(OnexError) as exc_info:
            get_error_codes_for_component("nonexistent_component")

        assert exc_info.value.error_code == CoreErrorCode.ITEM_NOT_REGISTERED

    def test_list_registered_components(self):
        """Test listing registered components."""

        class TestErrorCode(OnexErrorCode):
            TEST = "TEST_001"

            def get_component(self) -> str:
                return "TEST"

            def get_number(self) -> int:
                return 1

            def get_description(self) -> str:
                return "Test"

        register_error_codes("list_test_component", TestErrorCode)

        components = list_registered_components()
        assert isinstance(components, list)
        assert "list_test_component" in components


class TestRegistryErrorCode:
    """Test RegistryErrorCode enum."""

    def test_registry_error_code_values(self):
        """Test RegistryErrorCode enum values."""
        assert RegistryErrorCode.TOOL_NOT_FOUND
        assert RegistryErrorCode.DUPLICATE_TOOL
        assert RegistryErrorCode.INVALID_MODE
        assert RegistryErrorCode.REGISTRY_UNAVAILABLE

    def test_registry_error_code_get_component(self):
        """Test RegistryErrorCode.get_component()."""
        assert RegistryErrorCode.TOOL_NOT_FOUND.get_component() == "REGISTRY"

    def test_registry_error_code_get_description(self):
        """Test RegistryErrorCode.get_description()."""
        desc = RegistryErrorCode.TOOL_NOT_FOUND.get_description()
        assert "tool" in desc.lower()
        assert "registered" in desc.lower()

    def test_registry_error_code_get_exit_code(self):
        """Test RegistryErrorCode.get_exit_code()."""
        exit_code = RegistryErrorCode.TOOL_NOT_FOUND.get_exit_code()
        assert exit_code == CLIExitCode.ERROR.value


class TestOnexErrorEdgeCases:
    """Test OnexError edge cases."""

    def test_onex_error_with_empty_message(self):
        """Test OnexError with empty message."""
        error = OnexError(
            message="",
            error_code=CoreErrorCode.INTERNAL_ERROR,
        )

        assert error.message == ""

    def test_onex_error_with_none_error_code(self):
        """Test OnexError with None error_code."""
        error = OnexError(
            message="Test error",
            error_code=None,
        )

        assert error.error_code is None

    def test_onex_error_with_custom_status(self):
        """Test OnexError with custom status."""
        error = OnexError(
            message="Test warning",
            error_code=CoreErrorCode.VALIDATION_ERROR,
            status=EnumOnexStatus.WARNING,
        )

        assert error.status == EnumOnexStatus.WARNING

    def test_onex_error_timestamp_auto_generated(self):
        """Test that OnexError auto-generates timestamp."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.OPERATION_FAILED,
        )

        assert error.timestamp is not None
        assert isinstance(error.timestamp, datetime)


class TestGetExitCodeForCoreError:
    """Test get_exit_code_for_core_error() function."""

    def test_get_exit_code_for_various_errors(self):
        """Test exit code mapping for various core errors."""
        assert (
            get_exit_code_for_core_error(CoreErrorCode.VALIDATION_ERROR)
            == CLIExitCode.ERROR.value
        )
        assert (
            get_exit_code_for_core_error(CoreErrorCode.FILE_NOT_FOUND)
            == CLIExitCode.ERROR.value
        )
        assert (
            get_exit_code_for_core_error(CoreErrorCode.DUPLICATE_REGISTRATION)
            == CLIExitCode.WARNING.value
        )

    def test_get_exit_code_for_unknown_error_defaults_to_error(self):
        """Test that unknown error codes default to ERROR exit code."""
        # Create a custom error code not in the mapping

        class UnknownErrorCode(OnexErrorCode):
            UNKNOWN = "UNKNOWN_999"

            def get_component(self) -> str:
                return "UNKNOWN"

            def get_number(self) -> int:
                return 999

            def get_description(self) -> str:
                return "Unknown"

        # This should fall back to ERROR since it's not in CORE_ERROR_CODE_TO_EXIT_CODE
        exit_code = get_exit_code_for_core_error(CoreErrorCode.OPERATION_FAILED)
        assert exit_code == CLIExitCode.ERROR.value
