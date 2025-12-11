"""
Unit tests for reserved enum validation.

Tests validation enforcement for reserved enum values per NodeOrchestrator v1.0 contract.

This module tests:
- validate_execution_mode: Validates EnumExecutionMode enum values
- validate_execution_mode_string: Validates string-based execution modes
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.reserved_enum_validator import (
    RESERVED_EXECUTION_MODES,
    validate_execution_mode,
)
from omnibase_core.validation.workflow_validator import validate_execution_mode_string


class TestValidateExecutionMode:
    """Test suite for validate_execution_mode function."""

    def test_sequential_mode_accepted(self) -> None:
        """Test that SEQUENTIAL execution mode is accepted."""
        # Should not raise
        validate_execution_mode(EnumExecutionMode.SEQUENTIAL)

    def test_parallel_mode_accepted(self) -> None:
        """Test that PARALLEL execution mode is accepted."""
        # Should not raise
        validate_execution_mode(EnumExecutionMode.PARALLEL)

    def test_batch_mode_accepted(self) -> None:
        """Test that BATCH execution mode is accepted."""
        # Should not raise
        validate_execution_mode(EnumExecutionMode.BATCH)

    def test_conditional_mode_rejected(self) -> None:
        """Test that CONDITIONAL execution mode raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "conditional" in error.message.lower()
        assert "reserved" in error.message.lower()
        assert "v1.1+" in error.message or "future" in error.message.lower()

    def test_streaming_mode_rejected(self) -> None:
        """Test that STREAMING execution mode raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.STREAMING)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "streaming" in error.message.lower()
        assert "reserved" in error.message.lower()
        assert "v1.2+" in error.message or "future" in error.message.lower()

    def test_conditional_error_context(self) -> None:
        """Test that CONDITIONAL error includes proper context."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        error = exc_info.value
        # Context gets wrapped in "additional_context" by ModelOnexError
        context = error.context.get("additional_context", {})

        # Check context contains mode information
        assert "mode" in context
        assert context["mode"] == "conditional"

        # Check context lists reserved modes
        assert "reserved_modes" in context
        reserved_modes = context["reserved_modes"]
        assert "conditional" in reserved_modes
        assert "streaming" in reserved_modes

        # Check context lists accepted modes
        assert "accepted_modes" in context
        accepted_modes = context["accepted_modes"]
        assert "sequential" in accepted_modes
        assert "parallel" in accepted_modes
        assert "batch" in accepted_modes

    def test_streaming_error_context(self) -> None:
        """Test that STREAMING error includes proper context."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.STREAMING)

        error = exc_info.value
        # Context gets wrapped in "additional_context" by ModelOnexError
        context = error.context.get("additional_context", {})

        # Check context contains mode information
        assert "mode" in context
        assert context["mode"] == "streaming"

        # Check context lists reserved modes
        assert "reserved_modes" in context
        reserved_modes = context["reserved_modes"]
        assert "conditional" in reserved_modes
        assert "streaming" in reserved_modes

        # Check context lists accepted modes
        assert "accepted_modes" in context
        accepted_modes = context["accepted_modes"]
        assert "sequential" in accepted_modes
        assert "parallel" in accepted_modes
        assert "batch" in accepted_modes

    def test_error_code_is_validation_error(self) -> None:
        """Test that reserved mode errors use VALIDATION_ERROR code."""
        for reserved_mode in RESERVED_EXECUTION_MODES:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_execution_mode(reserved_mode)

            error = exc_info.value
            assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_message_contains_mode_name(self) -> None:
        """Test that error message includes the rejected mode name."""
        # Test CONDITIONAL
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)
        assert "conditional" in exc_info.value.message.lower()

        # Test STREAMING
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.STREAMING)
        assert "streaming" in exc_info.value.message.lower()

    def test_reserved_modes_constant(self) -> None:
        """Test that RESERVED_EXECUTION_MODES constant is correct."""
        assert EnumExecutionMode.CONDITIONAL in RESERVED_EXECUTION_MODES
        assert EnumExecutionMode.STREAMING in RESERVED_EXECUTION_MODES
        assert EnumExecutionMode.SEQUENTIAL not in RESERVED_EXECUTION_MODES
        assert EnumExecutionMode.PARALLEL not in RESERVED_EXECUTION_MODES
        assert EnumExecutionMode.BATCH not in RESERVED_EXECUTION_MODES


class TestReservedEnumValidatorIntegration:
    """Integration tests for reserved enum validator with workflow executor."""

    def test_all_accepted_modes_pass_validation(self) -> None:
        """Test that all accepted modes pass validation without errors."""
        accepted_modes = [
            EnumExecutionMode.SEQUENTIAL,
            EnumExecutionMode.PARALLEL,
            EnumExecutionMode.BATCH,
        ]

        for mode in accepted_modes:
            # Should not raise
            validate_execution_mode(mode)

    def test_all_reserved_modes_fail_validation(self) -> None:
        """Test that all reserved modes fail validation with proper errors."""
        for reserved_mode in RESERVED_EXECUTION_MODES:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_execution_mode(reserved_mode)

            error = exc_info.value
            assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert reserved_mode.value in error.message.lower()

    def test_error_is_modelonexerror_not_generic_exception(self) -> None:
        """Test that validation raises ModelOnexError, not generic Exception."""
        with pytest.raises(ModelOnexError):  # Specific type check
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        # Should NOT catch as generic Exception
        try:
            validate_execution_mode(EnumExecutionMode.STREAMING)
            pytest.fail("Expected ModelOnexError to be raised")
        except ModelOnexError:
            pass  # Expected
        except Exception:
            pytest.fail("Expected ModelOnexError, got generic Exception")


class TestErrorMessageQuality:
    """Test quality and clarity of error messages."""

    def test_conditional_error_message_clarity(self) -> None:
        """Test that CONDITIONAL error message is clear and actionable."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        message = exc_info.value.message.lower()

        # Message should explain what's wrong
        assert "conditional" in message
        assert "reserved" in message

        # Message should indicate when it's available
        assert "v1.1" in message or "future" in message

        # Message should indicate it's not accepted now
        assert "not accepted" in message or "not available" in message

    def test_streaming_error_message_clarity(self) -> None:
        """Test that STREAMING error message is clear and actionable."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.STREAMING)

        message = exc_info.value.message.lower()

        # Message should explain what's wrong
        assert "streaming" in message
        assert "reserved" in message

        # Message should indicate when it's available
        assert "v1.2" in message or "future" in message

        # Message should indicate it's not accepted now
        assert "not accepted" in message or "not available" in message

    def test_error_context_provides_alternatives(self) -> None:
        """Test that error context lists accepted alternatives."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        # Context gets wrapped in "additional_context" by ModelOnexError
        context = exc_info.value.context.get("additional_context", {})
        accepted_modes = context.get("accepted_modes", [])

        # Should list all valid alternatives
        assert "sequential" in accepted_modes
        assert "parallel" in accepted_modes
        assert "batch" in accepted_modes

        # Should not list reserved modes as alternatives
        assert "conditional" not in accepted_modes
        assert "streaming" not in accepted_modes


@pytest.mark.unit
class TestValidateExecutionModeString:
    """Test suite for validate_execution_mode_string function (string-based validation)."""

    def test_sequential_mode_string_accepted(self) -> None:
        """Test that 'sequential' string execution mode is accepted."""
        # Should not raise
        validate_execution_mode_string("sequential")

    def test_parallel_mode_string_accepted(self) -> None:
        """Test that 'parallel' string execution mode is accepted."""
        # Should not raise
        validate_execution_mode_string("parallel")

    def test_batch_mode_string_accepted(self) -> None:
        """Test that 'batch' string execution mode is accepted."""
        # Should not raise
        validate_execution_mode_string("batch")

    def test_conditional_mode_string_rejected(self) -> None:
        """Test that 'conditional' string execution mode raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("conditional")

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "conditional" in error.message.lower()
        assert "reserved" in error.message.lower()

    def test_streaming_mode_string_rejected(self) -> None:
        """Test that 'streaming' string execution mode raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("streaming")

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "streaming" in error.message.lower()
        assert "reserved" in error.message.lower()

    def test_case_insensitive_validation(self) -> None:
        """Test that string mode validation is case-insensitive."""
        # Valid modes in different cases should not raise
        validate_execution_mode_string("SEQUENTIAL")
        validate_execution_mode_string("Sequential")
        validate_execution_mode_string("PARALLEL")
        validate_execution_mode_string("Parallel")
        validate_execution_mode_string("BATCH")
        validate_execution_mode_string("Batch")

        # Reserved modes in different cases should raise
        with pytest.raises(ModelOnexError):
            validate_execution_mode_string("CONDITIONAL")

        with pytest.raises(ModelOnexError):
            validate_execution_mode_string("STREAMING")

    def test_conditional_string_error_context(self) -> None:
        """Test that 'conditional' string error includes proper context."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("conditional")

        error = exc_info.value
        # Context gets wrapped in "additional_context" by ModelOnexError
        context = error.context.get("additional_context", {})

        # Check context contains mode information
        assert "mode" in context
        assert context["mode"] == "conditional"

        # Check context lists reserved modes
        assert "reserved_modes" in context
        reserved_modes = context["reserved_modes"]
        assert "conditional" in reserved_modes
        assert "streaming" in reserved_modes

        # Check context lists accepted modes
        assert "accepted_modes" in context
        accepted_modes = context["accepted_modes"]
        assert "sequential" in accepted_modes
        assert "parallel" in accepted_modes
        assert "batch" in accepted_modes

    def test_streaming_string_error_context(self) -> None:
        """Test that 'streaming' string error includes proper context."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("streaming")

        error = exc_info.value
        # Context gets wrapped in "additional_context" by ModelOnexError
        context = error.context.get("additional_context", {})

        # Check context contains mode information
        assert "mode" in context
        assert context["mode"] == "streaming"

        # Check context lists reserved modes
        assert "reserved_modes" in context
        reserved_modes = context["reserved_modes"]
        assert "conditional" in reserved_modes
        assert "streaming" in reserved_modes

    def test_error_code_is_validation_error_for_string(self) -> None:
        """Test that reserved mode string errors use VALIDATION_ERROR code."""
        reserved_string_modes = ["conditional", "streaming"]

        for mode_str in reserved_string_modes:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_execution_mode_string(mode_str)

            error = exc_info.value
            assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_message_contains_mode_name_for_string(self) -> None:
        """Test that error message includes the rejected mode name."""
        # Test conditional
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("conditional")
        assert "conditional" in exc_info.value.message.lower()

        # Test streaming
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("streaming")
        assert "streaming" in exc_info.value.message.lower()


@pytest.mark.unit
class TestStringModeEdgeCases:
    """Test edge cases for string-based execution mode validation."""

    def test_all_accepted_string_modes_pass_validation(self) -> None:
        """Test that all accepted string modes pass validation without errors."""
        accepted_modes = ["sequential", "parallel", "batch"]

        for mode in accepted_modes:
            # Should not raise
            validate_execution_mode_string(mode)

    def test_all_reserved_string_modes_fail_validation(self) -> None:
        """Test that all reserved string modes fail validation with proper errors."""
        reserved_modes = ["conditional", "streaming"]

        for mode in reserved_modes:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_execution_mode_string(mode)

            error = exc_info.value
            assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert mode in error.message.lower()

    def test_string_validation_raises_modelonexerror_not_generic(self) -> None:
        """Test that string validation raises ModelOnexError, not generic Exception."""
        with pytest.raises(ModelOnexError):  # Specific type check
            validate_execution_mode_string("conditional")

        # Should NOT catch as generic Exception
        try:
            validate_execution_mode_string("streaming")
            pytest.fail("Expected ModelOnexError to be raised")
        except ModelOnexError:
            pass  # Expected
        except Exception:
            pytest.fail("Expected ModelOnexError, got generic Exception")
