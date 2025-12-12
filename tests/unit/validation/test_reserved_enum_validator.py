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


# =============================================================================
# Consolidation Tests (OMN-675)
# =============================================================================


@pytest.mark.unit
class TestValidatorConsolidation:
    """
    Test consolidation of validate_execution_mode validators.

    Per OMN-675, validates that:
    - Both validators enforce the same reserved modes
    - Both validators accept the same valid modes
    - Both validators produce consistent error codes
    - Public API exports are correct
    """

    def test_both_validators_reject_same_reserved_modes(self) -> None:
        """Test that both validators reject the same reserved modes."""
        # CONDITIONAL should be rejected by both
        with pytest.raises(ModelOnexError):
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)
        with pytest.raises(ModelOnexError):
            validate_execution_mode_string("conditional")

        # STREAMING should be rejected by both
        with pytest.raises(ModelOnexError):
            validate_execution_mode(EnumExecutionMode.STREAMING)
        with pytest.raises(ModelOnexError):
            validate_execution_mode_string("streaming")

    def test_both_validators_accept_same_valid_modes(self) -> None:
        """Test that both validators accept the same valid modes."""
        # SEQUENTIAL
        validate_execution_mode(EnumExecutionMode.SEQUENTIAL)
        validate_execution_mode_string("sequential")

        # PARALLEL
        validate_execution_mode(EnumExecutionMode.PARALLEL)
        validate_execution_mode_string("parallel")

        # BATCH
        validate_execution_mode(EnumExecutionMode.BATCH)
        validate_execution_mode_string("batch")

    def test_both_validators_use_same_error_code(self) -> None:
        """Test that both validators use VALIDATION_ERROR code."""
        # Enum validator
        with pytest.raises(ModelOnexError) as exc_info_enum:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        # String validator
        with pytest.raises(ModelOnexError) as exc_info_string:
            validate_execution_mode_string("conditional")

        # Both should use VALIDATION_ERROR
        assert exc_info_enum.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert exc_info_string.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reserved_modes_constant_consistency(self) -> None:
        """Test that reserved modes constants are consistent."""
        from omnibase_core.validation.workflow_validator import (
            RESERVED_EXECUTION_MODES as STRING_RESERVED_MODES,
        )

        # The string-based constant should contain lowercase versions
        assert "conditional" in STRING_RESERVED_MODES
        assert "streaming" in STRING_RESERVED_MODES

        # The enum-based constant should contain enum values
        assert EnumExecutionMode.CONDITIONAL in RESERVED_EXECUTION_MODES
        assert EnumExecutionMode.STREAMING in RESERVED_EXECUTION_MODES

    def test_accepted_modes_constant_exists_in_workflow_validator(self) -> None:
        """Test that ACCEPTED_EXECUTION_MODES constant exists and is correct."""
        from omnibase_core.validation.workflow_validator import ACCEPTED_EXECUTION_MODES

        assert "sequential" in ACCEPTED_EXECUTION_MODES
        assert "parallel" in ACCEPTED_EXECUTION_MODES
        assert "batch" in ACCEPTED_EXECUTION_MODES
        # Reserved modes should NOT be in accepted list
        assert "conditional" not in ACCEPTED_EXECUTION_MODES
        assert "streaming" not in ACCEPTED_EXECUTION_MODES


@pytest.mark.unit
class TestPublicAPIExports:
    """
    Test public API exports from validation __init__.py.

    Validates that the consolidation maintains backward compatibility
    by ensuring all expected symbols are exported correctly.
    """

    def test_validate_reserved_execution_mode_exported_from_validation(self) -> None:
        """Test that validate_reserved_execution_mode is exported from validation module."""
        from omnibase_core.validation import validate_reserved_execution_mode

        # Should work the same as validate_execution_mode
        # Valid modes should not raise
        validate_reserved_execution_mode(EnumExecutionMode.SEQUENTIAL)
        validate_reserved_execution_mode(EnumExecutionMode.PARALLEL)
        validate_reserved_execution_mode(EnumExecutionMode.BATCH)

        # Reserved modes should raise
        with pytest.raises(ModelOnexError):
            validate_reserved_execution_mode(EnumExecutionMode.CONDITIONAL)
        with pytest.raises(ModelOnexError):
            validate_reserved_execution_mode(EnumExecutionMode.STREAMING)

    def test_validate_execution_mode_string_exported_from_validation(self) -> None:
        """Test that validate_execution_mode_string is exported from validation module."""
        from omnibase_core.validation import validate_execution_mode_string as v_string

        # Valid modes should not raise
        v_string("sequential")
        v_string("parallel")
        v_string("batch")

        # Reserved modes should raise
        with pytest.raises(ModelOnexError):
            v_string("conditional")
        with pytest.raises(ModelOnexError):
            v_string("streaming")

    def test_reserved_execution_modes_constant_exported(self) -> None:
        """Test that RESERVED_EXECUTION_MODES is exported from validation module."""
        from omnibase_core.validation import RESERVED_EXECUTION_MODES as EXPORTED_CONST

        # Should contain the enum values
        assert EnumExecutionMode.CONDITIONAL in EXPORTED_CONST
        assert EnumExecutionMode.STREAMING in EXPORTED_CONST

    def test_validate_reserved_execution_mode_is_alias(self) -> None:
        """Test that validate_reserved_execution_mode is an alias for validate_execution_mode."""
        from omnibase_core.validation import validate_reserved_execution_mode
        from omnibase_core.validation.reserved_enum_validator import (
            validate_execution_mode,
        )

        # They should be the exact same function
        assert validate_reserved_execution_mode is validate_execution_mode


@pytest.mark.unit
class TestInvalidInputHandling:
    """
    Test handling of invalid inputs by validators.

    These tests ensure proper error handling for edge cases.
    """

    def test_string_validator_rejects_unknown_modes(self) -> None:
        """
        Test string validator behavior with unknown mode strings.

        The validator first validates that the mode is a valid EnumExecutionMode,
        then checks if it's reserved. Unknown modes should raise ModelOnexError.
        """
        # Unknown modes should raise - they're not valid execution modes
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("unknown_mode")
        assert "Invalid execution mode" in exc_info.value.message

        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("foobar")
        assert "Invalid execution mode" in exc_info.value.message

        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("")  # Empty string is not valid
        assert "Invalid execution mode" in exc_info.value.message

    def test_string_validator_normalizes_to_lowercase_in_error_for_reserved(
        self,
    ) -> None:
        """
        Test that error context contains mode information for reserved modes.

        The validator stores the lowercase version in context for consistency.
        """
        test_cases = ["CONDITIONAL", "Conditional", "conditional"]

        for mode in test_cases:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_execution_mode_string(mode)

            # Error should mention the reserved mode
            assert "reserved" in exc_info.value.message.lower()

    def test_string_validator_whitespace_raises_invalid_mode(self) -> None:
        """
        Test string validator with whitespace in mode strings.

        Modes with leading/trailing whitespace are not valid EnumExecutionMode values.
        """
        # These should raise as invalid modes (not matching enum values)
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string(" conditional")
        assert "Invalid execution mode" in exc_info.value.message

        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("conditional ")
        assert "Invalid execution mode" in exc_info.value.message

        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string(" conditional ")
        assert "Invalid execution mode" in exc_info.value.message

    def test_enum_validator_error_includes_version_info(self) -> None:
        """Test that enum validator error includes version information."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.CONDITIONAL)

        context = exc_info.value.context.get("additional_context", {})
        assert "version" in context
        assert "v1.1" in context["version"]

        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode(EnumExecutionMode.STREAMING)

        context = exc_info.value.context.get("additional_context", {})
        assert "version" in context
        assert "v1.2" in context["version"]

    def test_string_validator_error_lists_valid_modes(self) -> None:
        """Test that string validator error for unknown mode lists valid options."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_execution_mode_string("invalid_mode")

        message = exc_info.value.message
        # Should clearly distinguish accepted modes from reserved (future) modes
        assert "Accepted modes:" in message
        assert "sequential" in message
        assert "parallel" in message
        assert "batch" in message
        assert "Reserved (future):" in message


@pytest.mark.unit
class TestBackwardCompatibility:
    """
    Test backward compatibility of validator consolidation.

    Ensures that code using the old API continues to work correctly.
    """

    def test_direct_import_from_reserved_enum_validator(self) -> None:
        """Test that direct import from reserved_enum_validator still works."""
        from omnibase_core.validation.reserved_enum_validator import (
            RESERVED_EXECUTION_MODES,
            validate_execution_mode,
        )

        # Should still work
        validate_execution_mode(EnumExecutionMode.SEQUENTIAL)
        assert EnumExecutionMode.CONDITIONAL in RESERVED_EXECUTION_MODES

    def test_direct_import_from_workflow_validator(self) -> None:
        """Test that direct import from workflow_validator still works."""
        from omnibase_core.validation.workflow_validator import (
            ACCEPTED_EXECUTION_MODES,
            RESERVED_EXECUTION_MODES,
            validate_execution_mode_string,
        )

        # Should still work
        validate_execution_mode_string("sequential")
        assert "conditional" in RESERVED_EXECUTION_MODES
        assert "sequential" in ACCEPTED_EXECUTION_MODES

    def test_import_from_validation_init(self) -> None:
        """Test that import from validation __init__ works correctly."""
        from omnibase_core.validation import (
            RESERVED_EXECUTION_MODES,
            validate_execution_mode_string,
            validate_reserved_execution_mode,
        )

        # All imports should work
        validate_reserved_execution_mode(EnumExecutionMode.SEQUENTIAL)
        validate_execution_mode_string("sequential")
        assert EnumExecutionMode.CONDITIONAL in RESERVED_EXECUTION_MODES
