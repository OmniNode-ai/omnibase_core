"""
Test suite for MixinFailFast.
"""

from unittest.mock import Mock, patch

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_fail_fast import MixinFailFast
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestMixinFailFast:
    """Test MixinFailFast functionality."""

    def test_mixin_fail_fast_initialization(self):
        """Test MixinFailFast initialization."""
        mixin = MixinFailFast()

        assert hasattr(mixin, "fail_fast")
        assert hasattr(mixin, "validate_required")
        assert hasattr(mixin, "validate_not_empty")
        assert hasattr(mixin, "validate_type")
        assert hasattr(mixin, "validate_enum")
        assert hasattr(mixin, "require_dependency")
        assert hasattr(mixin, "enforce_contract")

    def test_validate_required_with_valid_value(self):
        """Test validate_required with valid value."""
        mixin = MixinFailFast()

        result = mixin.validate_required("test_value", "test_field")
        assert result == "test_value"

    def test_validate_required_with_none_value(self):
        """Test validate_required with None value."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_required(None, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "Required field 'test_field' is missing" in str(exc_info.value)

    def test_validate_not_empty_with_valid_value(self):
        """Test validate_not_empty with valid value."""
        mixin = MixinFailFast()

        result = mixin.validate_not_empty("test", "test_field")
        assert result == "test"

        result = mixin.validate_not_empty([1, 2, 3], "test_field")
        assert result == [1, 2, 3]

    def test_validate_not_empty_with_empty_value(self):
        """Test validate_not_empty with empty value."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_not_empty("", "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "Field 'test_field' cannot be empty" in str(exc_info.value)

    def test_validate_not_empty_with_none_value(self):
        """Test validate_not_empty with None value."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_not_empty(None, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_not_empty_with_empty_list(self):
        """Test validate_not_empty with empty list."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_not_empty([], "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_type_with_matching_type(self):
        """Test validate_type with matching type."""
        mixin = MixinFailFast()

        result = mixin.validate_type("test", str, "test_field")
        assert result == "test"

        result = mixin.validate_type(42, int, "test_field")
        assert result == 42

    def test_validate_type_with_non_matching_type(self):
        """Test validate_type with non-matching type."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_type(42, str, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "Field 'test_field' must be compatible with type str" in str(
            exc_info.value
        )

    def test_validate_enum_with_valid_value(self):
        """Test validate_enum with valid value."""
        mixin = MixinFailFast()

        allowed_values = ["option1", "option2", "option3"]
        result = mixin.validate_enum("option1", allowed_values, "test_field")
        assert result == "option1"

    def test_validate_enum_with_invalid_value(self):
        """Test validate_enum with invalid value."""
        mixin = MixinFailFast()

        allowed_values = ["option1", "option2", "option3"]
        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_enum("invalid", allowed_values, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "Field 'test_field' must be one of" in str(exc_info.value)

    def test_require_dependency_with_available_dependency(self):
        """Test require_dependency with available dependency."""
        mixin = MixinFailFast()

        def check_func():
            return True

        # Should not raise
        mixin.require_dependency("test_dep", check_func)

    def test_require_dependency_with_unavailable_dependency(self):
        """Test require_dependency with unavailable dependency."""
        mixin = MixinFailFast()

        def check_func():
            return False

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.require_dependency("test_dep", check_func)

        assert exc_info.value.error_code == EnumCoreErrorCode.DEPENDENCY_FAILED
        assert "Required dependency 'test_dep' is not available" in str(exc_info.value)

    def test_require_dependency_with_exception(self):
        """Test require_dependency with exception in check function."""
        mixin = MixinFailFast()

        def check_func():
            raise ValueError("Check failed")

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.require_dependency("test_dep", check_func)

        assert exc_info.value.error_code == EnumCoreErrorCode.DEPENDENCY_FAILED
        assert "Failed to check dependency 'test_dep'" in str(exc_info.value)

    def test_enforce_contract_with_valid_condition(self):
        """Test enforce_contract with valid condition."""
        mixin = MixinFailFast()

        # Should not raise
        mixin.enforce_contract(True, "Test message", "test_field")

    def test_enforce_contract_with_invalid_condition(self):
        """Test enforce_contract with invalid condition."""
        mixin = MixinFailFast()

        with pytest.raises(ModelOnexError) as exc_info:
            mixin.enforce_contract(False, "Contract violated", "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION
        assert "Contract violated" in str(exc_info.value)

    def test_fail_fast_decorator_with_success(self):
        """Test fail_fast decorator with successful function."""
        mixin = MixinFailFast()

        @mixin.fail_fast
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_fail_fast_decorator_with_exception(self):
        """Test fail_fast decorator with exception."""
        mixin = MixinFailFast()

        @mixin.fail_fast
        def test_func():
            raise ValueError("Test error")

        # Mock _handle_critical_error to avoid sys.exit
        with patch.object(mixin, "_handle_critical_error") as mock_handle:
            with pytest.raises(
                Exception
            ):  # Should be converted to ExceptionFailFastError
                test_func()
            mock_handle.assert_called_once()

    def test_handle_error_with_model_onex_error(self):
        """Test handle_error with ModelOnexError."""
        mixin = MixinFailFast()

        # Create a mock error that has error_code and details attributes
        mock_error = Mock()
        mock_error.error_code = "TEST_ERROR"
        mock_error.details = {"key": "value"}

        # Mock the _handle_critical_error method to avoid sys.exit
        with patch.object(mixin, "_handle_critical_error") as mock_handle:
            mixin.handle_error(mock_error, "test_context")
            mock_handle.assert_called_once()

    def test_handle_error_with_regular_exception(self):
        """Test handle_error with regular exception."""
        mixin = MixinFailFast()

        error = ValueError("Regular error")

        # Mock emit_log_event to avoid actual logging
        with patch("omnibase_core.mixins.mixin_fail_fast.emit_log_event") as mock_emit:
            mixin.handle_error(error, "test_context")
            mock_emit.assert_called_once()

    def test_validate_type_with_list_type(self):
        """Test validate_type with list type."""
        mixin = MixinFailFast()

        # Valid list
        result = mixin.validate_type([1, 2, 3], list, "test_field")
        assert result == [1, 2, 3]

        # Invalid type for list
        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_type("not_a_list", list, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_type_with_dict_type(self):
        """Test validate_type with dict type."""
        mixin = MixinFailFast()

        # Valid dict
        result = mixin.validate_type({"key": "value"}, dict, "test_field")
        assert result == {"key": "value"}

        # Invalid type for dict
        with pytest.raises(ModelOnexError) as exc_info:
            mixin.validate_type("not_a_dict", dict, "test_field")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
