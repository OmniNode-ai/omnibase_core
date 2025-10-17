"""
Tests for ModelCLIAdapter - CLI adapter with consistent exit code handling.

This module tests the CLI adapter's exit code mapping, status handling,
and error reporting functionality.
"""

import sys
from unittest.mock import Mock, call, patch
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter


class TestExitWithStatus:
    """Test exit_with_status functionality."""

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_success(self, mock_get_exit, mock_emit, mock_sys_exit):
        """Test exit with SUCCESS status."""
        mock_get_exit.return_value = 0

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.SUCCESS)

        mock_get_exit.assert_called_once_with(EnumOnexStatus.SUCCESS)
        mock_sys_exit.assert_called_once_with(0)
        # No logging for success without message
        mock_emit.assert_not_called()

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_error(self, mock_get_exit, mock_emit, mock_sys_exit):
        """Test exit with ERROR status."""
        mock_get_exit.return_value = 1

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.ERROR)

        mock_get_exit.assert_called_once_with(EnumOnexStatus.ERROR)
        mock_sys_exit.assert_called_once_with(1)

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_warning(self, mock_get_exit, mock_emit, mock_sys_exit):
        """Test exit with WARNING status."""
        mock_get_exit.return_value = 2

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.WARNING)

        mock_get_exit.assert_called_once_with(EnumOnexStatus.WARNING)
        mock_sys_exit.assert_called_once_with(2)

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_unknown(self, mock_get_exit, mock_emit, mock_sys_exit):
        """Test exit with UNKNOWN status."""
        mock_get_exit.return_value = 255

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.UNKNOWN)

        mock_get_exit.assert_called_once_with(EnumOnexStatus.UNKNOWN)
        mock_sys_exit.assert_called_once_with(255)

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_with_message_error(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test exit with ERROR status and message logs error."""
        mock_get_exit.return_value = 1
        message = "Operation failed"

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.ERROR, message)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args.kwargs["level"] == EnumEvents.ERROR
        assert call_args.kwargs["message"] == message
        assert call_args.kwargs["event_type"] == "cli_exit_error"
        assert call_args.kwargs["data"]["status"] == EnumOnexStatus.ERROR.value
        assert call_args.kwargs["data"]["exit_code"] == 1

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_with_message_warning(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test exit with WARNING status and message logs warning."""
        mock_get_exit.return_value = 2
        message = "Completed with warnings"

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.WARNING, message)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args.kwargs["level"] == EnumEvents.WARNING
        assert call_args.kwargs["message"] == message
        assert call_args.kwargs["event_type"] == "cli_exit_warning"

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_with_message_success(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test exit with SUCCESS status and message logs info."""
        mock_get_exit.return_value = 0
        message = "Operation completed successfully"

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.SUCCESS, message)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args.kwargs["level"] == EnumEvents.INFO
        assert call_args.kwargs["message"] == message
        assert call_args.kwargs["event_type"] == "cli_exit_info"

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_exit_with_status_empty_message_no_logging(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test exit with empty message doesn't trigger logging."""
        mock_get_exit.return_value = 0

        ModelCLIAdapter.exit_with_status(EnumOnexStatus.SUCCESS, "")

        mock_emit.assert_not_called()
        mock_sys_exit.assert_called_once_with(0)


class TestExitWithError:
    """Test exit_with_error functionality."""

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_exit_with_error_basic(self, mock_emit, mock_sys_exit):
        """Test exit with basic error."""
        correlation_id = uuid4()
        error = ModelOnexError(
            message="Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            correlation_id=correlation_id,
        )

        ModelCLIAdapter.exit_with_error(error)

        mock_sys_exit.assert_called_once()
        exit_code = mock_sys_exit.call_args[0][0]
        assert isinstance(exit_code, int)

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args.kwargs["level"] == EnumEvents.ERROR
        assert "Test error" in call_args.kwargs["message"]
        assert call_args.kwargs["event_type"] == "cli_exit_with_error"
        assert call_args.kwargs["correlation_id"] == correlation_id

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_exit_with_error_with_context(self, mock_emit, mock_sys_exit):
        """Test exit with error containing context."""
        correlation_id = uuid4()
        error = ModelOnexError(
            message="Validation failed",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            correlation_id=correlation_id,
            context={"field": "email", "value": "invalid"},
        )

        ModelCLIAdapter.exit_with_error(error)

        call_args = mock_emit.call_args
        # ModelOnexError wraps context in additional_context
        assert "context" in call_args.kwargs["data"]
        assert "additional_context" in call_args.kwargs["data"]["context"]
        assert "context" in call_args.kwargs["data"]["context"]["additional_context"]
        inner_context = call_args.kwargs["data"]["context"]["additional_context"][
            "context"
        ]
        assert inner_context["field"] == "email"
        assert inner_context["value"] == "invalid"

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_exit_with_error_logs_error_code(self, mock_emit, mock_sys_exit):
        """Test exit with error logs error code."""
        error = ModelOnexError(
            message="Test error",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )

        ModelCLIAdapter.exit_with_error(error)

        call_args = mock_emit.call_args
        assert call_args.kwargs["data"]["error_code"] == str(
            EnumCoreErrorCode.OPERATION_FAILED
        )

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_exit_with_error_logs_exit_code(self, mock_emit, mock_sys_exit):
        """Test exit with error logs exit code."""
        error = ModelOnexError(
            message="Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        ModelCLIAdapter.exit_with_error(error)

        call_args = mock_emit.call_args
        exit_code = call_args.kwargs["data"]["exit_code"]
        assert isinstance(exit_code, int)
        assert exit_code > 0

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_exit_with_error_without_error_code(self, mock_emit, mock_sys_exit):
        """Test exit with error without explicit error code."""
        error = ModelOnexError(message="Test error without code")

        ModelCLIAdapter.exit_with_error(error)

        call_args = mock_emit.call_args
        # Should handle None error_code gracefully
        error_code = call_args.kwargs["data"]["error_code"]
        assert error_code is None or isinstance(error_code, str)


class TestAdapterStaticMethods:
    """Test adapter static methods."""

    def test_exit_with_status_is_static(self):
        """Test exit_with_status is a static method."""
        assert isinstance(ModelCLIAdapter.__dict__["exit_with_status"], staticmethod)

    def test_exit_with_error_is_static(self):
        """Test exit_with_error is a static method."""
        assert isinstance(ModelCLIAdapter.__dict__["exit_with_error"], staticmethod)


class TestAdapterIntegration:
    """Test adapter integration scenarios."""

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_multiple_status_types_map_correctly(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test different status types map to correct exit codes."""
        test_cases = [
            (EnumOnexStatus.SUCCESS, 0),
            (EnumOnexStatus.ERROR, 1),
            (EnumOnexStatus.WARNING, 2),
            (EnumOnexStatus.UNKNOWN, 255),
        ]

        for status, expected_code in test_cases:
            mock_get_exit.return_value = expected_code
            mock_sys_exit.reset_mock()

            ModelCLIAdapter.exit_with_status(status)

            mock_sys_exit.assert_called_once_with(expected_code)

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    def test_error_with_all_fields_logs_completely(self, mock_emit, mock_sys_exit):
        """Test error with all fields logs all information."""
        correlation_id = uuid4()
        error = ModelOnexError(
            message="Complete error test",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            correlation_id=correlation_id,
            context={
                "operation": "validate_input",
                "field": "username",
                "constraint": "min_length",
            },
        )

        ModelCLIAdapter.exit_with_error(error)

        call_args = mock_emit.call_args.kwargs
        assert call_args["level"] == EnumEvents.ERROR
        assert "Complete error test" in call_args["message"]
        assert call_args["event_type"] == "cli_exit_with_error"
        assert call_args["correlation_id"] == correlation_id
        # ModelOnexError wraps context in additional_context
        inner_context = call_args["data"]["context"]["additional_context"]["context"]
        assert "operation" in inner_context
        assert "field" in inner_context
        assert "constraint" in inner_context

    @patch("sys.exit")
    @patch("omnibase_core.models.core.model_cli_adapter.emit_log_event_sync")
    @patch("omnibase_core.models.core.model_cli_adapter.get_exit_code_for_status")
    def test_status_and_error_exit_codes_consistent(
        self, mock_get_exit, mock_emit, mock_sys_exit
    ):
        """Test status-based and error-based exits use consistent codes."""
        mock_get_exit.return_value = 1

        # Exit with ERROR status
        ModelCLIAdapter.exit_with_status(EnumOnexStatus.ERROR, "Status error")
        status_exit_code = mock_sys_exit.call_args[0][0]

        mock_sys_exit.reset_mock()

        # Exit with validation error
        error = ModelOnexError(
            message="Error object",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
        ModelCLIAdapter.exit_with_error(error)
        error_exit_code = mock_sys_exit.call_args[0][0]

        # Both should use non-zero exit codes
        assert status_exit_code != 0
        assert error_exit_code != 0


class TestAdapterExportedSymbols:
    """Test adapter exports correct symbols."""

    def test_adapter_class_exported(self):
        """Test ModelCLIAdapter is exported."""
        from omnibase_core.models.core.model_cli_adapter import __all__

        assert "ModelCLIAdapter" in __all__

    def test_only_expected_symbols_exported(self):
        """Test only expected symbols are exported."""
        from omnibase_core.models.core.model_cli_adapter import __all__

        assert len(__all__) == 1
        assert __all__ == ["ModelCLIAdapter"]
