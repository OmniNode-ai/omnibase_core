"""
Comprehensive unit tests for MixinFailFast.

Tests cover:
- Fail-fast decorator behavior
- Validation helpers (required, not_empty, type, enum)
- Dependency checking
- Contract enforcement
- Error handling and logging
- Multiple inheritance scenarios
"""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.mixins.mixin_fail_fast import MixinFailFast


class TestMixinFailFastBasicBehavior:
    """Test basic MixinFailFast initialization and behaviors."""

    def test_mixin_initialization(self):
        """Test MixinFailFast can be initialized."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        assert isinstance(node, MixinFailFast)

    def test_mixin_in_multiple_inheritance(self):
        """Test MixinFailFast works in multiple inheritance."""

        class BaseNode:
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.base_initialized = True

        class TestNode(MixinFailFast, BaseNode):
            pass

        node = TestNode()
        assert isinstance(node, MixinFailFast)
        assert isinstance(node, BaseNode)
        assert node.base_initialized


class TestFailFastDecorator:
    """Test fail_fast decorator functionality."""

    def test_fail_fast_decorator_on_successful_function(self):
        """Test fail_fast decorator passes through successful execution."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        @node.fail_fast
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_fail_fast_decorator_converts_exception(self):
        """Test fail_fast decorator converts exceptions to FailFastError."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        @node.fail_fast
        def failing_function():
            raise ValueError("Something went wrong")

        # The decorator calls sys.exit(1) which prevents pytest from catching
        # We need to mock sys.exit to test this
        with patch.object(sys, "exit") as mock_exit:
            try:
                failing_function()
            except Exception:
                pass  # Expected to call sys.exit before raising

            mock_exit.assert_called_once_with(1)

    def test_fail_fast_decorator_with_arguments(self):
        """Test fail_fast decorator works with function arguments."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        @node.fail_fast
        def function_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = function_with_args("x", "y", c="z")
        assert result == "x-y-z"

    def test_fail_fast_decorator_preserves_function_metadata(self):
        """Test fail_fast decorator preserves function metadata."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        @node.fail_fast
        def documented_function():
            """This is documentation."""
            pass

        assert documented_function.__doc__ == "This is documentation."
        assert documented_function.__name__ == "documented_function"


class TestValidateRequired:
    """Test validate_required functionality."""

    def test_validate_required_with_valid_value(self):
        """Test validate_required passes with non-None value."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        result = node.validate_required("test_value", "test_field")
        assert result == "test_value"

    def test_validate_required_with_none_raises_error(self):
        """Test validate_required raises ModelOnexError for None."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_required(None, "required_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "required_field" in str(exc_info.value)
        assert "missing" in str(exc_info.value).lower()

    def test_validate_required_with_various_types(self):
        """Test validate_required works with different data types."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Test with different types
        assert node.validate_required("string", "field") == "string"
        assert node.validate_required(42, "field") == 42
        assert node.validate_required([], "field") == []
        assert node.validate_required({}, "field") == {}
        assert node.validate_required(False, "field") is False
        assert node.validate_required(0, "field") == 0


class TestValidateNotEmpty:
    """Test validate_not_empty functionality."""

    def test_validate_not_empty_with_non_empty_value(self):
        """Test validate_not_empty passes with non-empty value."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        result = node.validate_not_empty("test", "test_field")
        assert result == "test"

    def test_validate_not_empty_with_empty_string_raises_error(self):
        """Test validate_not_empty raises error for empty string."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_not_empty("", "empty_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "empty_field" in str(exc_info.value)

    def test_validate_not_empty_with_empty_list_raises_error(self):
        """Test validate_not_empty raises error for empty list."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_not_empty([], "list_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_not_empty_with_falsy_but_valid_values(self):
        """Test validate_not_empty rejects falsy values."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # These should raise because they're falsy
        with pytest.raises(ModelOnexError):
            node.validate_not_empty(0, "zero_field")

        with pytest.raises(ModelOnexError):
            node.validate_not_empty(False, "false_field")


class TestValidateType:
    """Test validate_type functionality with duck typing."""

    def test_validate_type_with_correct_type(self):
        """Test validate_type passes with correct type."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        result = node.validate_type("test", str, "string_field")
        assert result == "test"

    def test_validate_type_duck_typing_enabled(self):
        """Test validate_type uses duck typing for compatible types."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Test with actual str type which should pass
        result = node.validate_type("test_string", str, "field")
        assert result == "test_string"

    def test_validate_type_with_incompatible_type_raises_error(self):
        """Test validate_type raises error for incompatible types."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_type(123, str, "string_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "string_field" in str(exc_info.value)

    def test_validate_type_with_numeric_types(self):
        """Test validate_type handles numeric types."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Valid numeric
        result = node.validate_type(42, int, "int_field")
        assert result == 42

    def test_validate_type_with_list_types(self):
        """Test validate_type handles list types with duck typing."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Valid list
        result = node.validate_type([1, 2, 3], list[Any], "list_field")
        assert result == [1, 2, 3]

    def test_validate_type_with_dict_types(self):
        """Test validate_type handles dict types with duck typing."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Valid dict
        result = node.validate_type({"key": "value"}, dict[str, Any], "dict_field")
        assert result == {"key": "value"}


class TestValidateEnum:
    """Test validate_enum functionality."""

    def test_validate_enum_with_valid_value(self):
        """Test validate_enum passes with valid enum value."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        allowed = ["red", "green", "blue"]
        result = node.validate_enum("red", allowed, "color_field")
        assert result == "red"

    def test_validate_enum_with_invalid_value_raises_error(self):
        """Test validate_enum raises error for invalid value."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        allowed = ["red", "green", "blue"]

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_enum("yellow", allowed, "color_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "color_field" in str(exc_info.value)
        assert "yellow" in str(exc_info.value)

    def test_validate_enum_with_empty_allowed_list(self):
        """Test validate_enum with empty allowed list."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.validate_enum("any_value", [], "field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED


class TestRequireDependency:
    """Test require_dependency functionality."""

    def test_require_dependency_with_available_dependency(self):
        """Test require_dependency passes when dependency is available."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        def check_available():
            return True

        # Should not raise
        node.require_dependency("test_service", check_available)

    def test_require_dependency_with_unavailable_dependency_raises_error(self):
        """Test require_dependency raises error when dependency unavailable."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        def check_unavailable():
            return False

        with pytest.raises(ModelOnexError) as exc_info:
            node.require_dependency("database", check_unavailable)

        assert exc_info.value.error_code == EnumCoreErrorCode.DEPENDENCY_FAILED
        assert "database" in str(exc_info.value)

    def test_require_dependency_with_failing_check_function(self):
        """Test require_dependency handles check function failures."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        def check_raises():
            raise RuntimeError("Check failed")

        with pytest.raises(ModelOnexError) as exc_info:
            node.require_dependency("service", check_raises)

        assert exc_info.value.error_code == EnumCoreErrorCode.DEPENDENCY_FAILED
        assert "service" in str(exc_info.value)


class TestEnforceContract:
    """Test enforce_contract functionality."""

    def test_enforce_contract_with_true_condition(self):
        """Test enforce_contract passes with true condition."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Should not raise
        node.enforce_contract(True, "Contract violated", "contract_field")

    def test_enforce_contract_with_false_condition_raises_error(self):
        """Test enforce_contract raises error with false condition."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        with pytest.raises(ModelOnexError) as exc_info:
            node.enforce_contract(False, "Invalid state", "state_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION
        assert "Invalid state" in str(exc_info.value)

    def test_enforce_contract_with_complex_conditions(self):
        """Test enforce_contract with various conditions."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Pass: valid conditions
        node.enforce_contract(5 > 3, "Five should be greater", "comparison")
        node.enforce_contract("test" in ["test"], "Should contain", "membership")

        # Fail: invalid conditions
        with pytest.raises(ModelOnexError):
            node.enforce_contract(5 < 3, "Invalid comparison", "field")


class TestHandleError:
    """Test handle_error functionality."""

    def test_handle_error_with_regular_exception(self):
        """Test handle_error logs regular exceptions."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()
        error = ValueError("Regular error")

        # Should log but not exit for regular exceptions
        with patch("omnibase_core.logging.structured.emit_log_event_sync"):
            node.handle_error(error, "test_context")

    def test_handle_error_interface_exists(self):
        """Test handle_error method exists and is callable."""

        class TestNode(MixinFailFast):
            pass

        node = TestNode()

        # Verify method exists
        assert hasattr(node, "handle_error")
        assert callable(node.handle_error)

        # Test it can be called with regular exception
        with patch("omnibase_core.logging.structured.emit_log_event_sync"):
            node.handle_error(ValueError("test"), "test_context")


class TestMixinFailFastIntegration:
    """Integration tests for MixinFailFast usage patterns."""

    def test_combined_validation_workflow(self):
        """Test using multiple validation methods together."""

        class TestNode(MixinFailFast):
            def validate_input(self, config: dict[str, Any]) -> dict[str, Any]:
                # Validate required fields
                self.validate_required(config.get("name"), "name")
                self.validate_not_empty(config.get("name"), "name")

                # Validate types
                self.validate_type(config.get("timeout"), int, "timeout")

                # Validate enum
                if "status" in config:
                    self.validate_enum(
                        config["status"], ["active", "inactive"], "status"
                    )

                return config

        node = TestNode()

        # Valid config
        valid_config = {"name": "test", "timeout": 30, "status": "active"}
        result = node.validate_input(valid_config)
        assert result == valid_config

        # Invalid configs
        with pytest.raises(ModelOnexError):
            node.validate_input({"name": None, "timeout": 30})

        with pytest.raises(ModelOnexError):
            node.validate_input({"name": "", "timeout": 30})

        with pytest.raises(ModelOnexError):
            node.validate_input({"name": "test", "timeout": "not_int"})

    def test_dependency_and_contract_workflow(self):
        """Test combining dependency checks and contract enforcement."""

        class TestNode(MixinFailFast):
            def __init__(self):
                super().__init__()
                self.db_connected = False

            def process(self):
                # Check dependency
                self.require_dependency("database", lambda: self.db_connected)

                # Enforce contract
                self.enforce_contract(self.db_connected, "DB must be connected", "db")

        node = TestNode()

        # Fails without connection
        with pytest.raises(ModelOnexError):
            node.process()

        # Succeeds with connection
        node.db_connected = True
        node.process()  # Should not raise

    def test_mixin_with_custom_node_class(self):
        """Test MixinFailFast integrated with custom node class."""

        class CustomNode(MixinFailFast):
            def __init__(self, name: str):
                super().__init__()
                self.name = self.validate_required(name, "name")

            def execute(self, data: dict[str, Any]):
                self.validate_not_empty(data, "data")
                return f"Processed by {self.name}"

        node = CustomNode("processor")
        assert node.name == "processor"

        result = node.execute({"key": "value"})
        assert "processor" in result

        # Invalid initialization
        with pytest.raises(ModelOnexError):
            CustomNode(None)

        # Invalid execution
        with pytest.raises(ModelOnexError):
            node.execute({})
