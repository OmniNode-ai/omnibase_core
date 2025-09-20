"""
Unit tests for CLI execution model type safety fixes.

Tests the elimination of dict[str, Any] violations and proper typing.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from src.omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from src.omnibase_core.models.cli.model_cli_command_option import ModelCliCommandOption
from src.omnibase_core.models.cli.model_cli_execution import ModelCliExecution
from src.omnibase_core.models.cli.model_cli_execution_context import (
    ModelCliExecutionContext,
)
from src.omnibase_core.models.cli.model_cli_execution_input_data import (
    ModelCliExecutionInputData,
)
from src.omnibase_core.models.cli.model_cli_execution_summary import (
    ModelCliExecutionSummary,
)


class TestModelCliExecutionTyping:
    """Test CLI execution model with proper typing."""

    def test_command_options_typed_properly(self):
        """Test that command options use proper typing instead of dict[str, Any]."""
        execution = ModelCliExecution(command_name="test-command")

        # Create a properly typed command option
        option = ModelCliCommandOption(
            name="--verbose",
            value=True,
            is_flag=True,
            description="Enable verbose output",
        )

        # Add the option (should not be dict[str, Any])
        execution.command_options["verbose"] = option

        # Verify proper typing
        assert isinstance(execution.command_options["verbose"], ModelCliCommandOption)
        assert execution.command_options["verbose"].name == "--verbose"
        assert execution.command_options["verbose"].value is True

    def test_input_data_typed_properly(self):
        """Test that input data uses proper typing instead of dict[str, Any]."""
        execution = ModelCliExecution(command_name="test-command")

        # Create properly typed input data
        input_data = ModelCliExecutionInputData(
            key="file_path",
            value=Path("/test/path"),
            data_type="path",
            description="Input file path",
        )

        # Add input data using the typed method
        execution.add_input_data("file_path", input_data)

        # Verify proper typing
        retrieved = execution.get_input_data("file_path")
        assert isinstance(retrieved, ModelCliExecutionInputData)
        assert retrieved.key == "file_path"
        assert isinstance(retrieved.value, Path)

    def test_custom_context_typed_properly(self):
        """Test that custom context uses proper typing instead of dict[str, Any]."""
        execution = ModelCliExecution(command_name="test-command")

        # Create properly typed context
        context = ModelCliExecutionContext(
            key="user_id",
            value=uuid4(),
            context_type="identity",
            description="User identifier",
        )

        # Add context using the typed method
        execution.add_context("user_id", context)

        # Verify proper typing
        retrieved = execution.get_context("user_id")
        assert isinstance(retrieved, ModelCliExecutionContext)
        assert retrieved.key == "user_id"
        assert isinstance(retrieved.value, UUID)

    def test_execution_summary_returns_typed_model(self):
        """Test that get_summary returns proper model instead of dict[str, Any]."""
        execution = ModelCliExecution(
            command_name="test-command",
            target_node_name="test-node",
            status=EnumExecutionStatus.SUCCESS,
            current_phase=EnumExecutionPhase.EXECUTION,
            progress_percentage=100.0,
        )

        # Get summary - should return typed model
        summary = execution.get_summary()

        # Verify it's a proper model, not dict[str, Any]
        assert isinstance(summary, ModelCliExecutionSummary)
        assert summary.command_name == "test-command"
        assert summary.target_node_name == "test-node"
        assert summary.status == EnumExecutionStatus.SUCCESS
        assert summary.progress_percentage == 100.0

        # Verify methods work on the typed summary
        assert summary.is_successful() is True
        assert summary.is_completed() is False  # No end_time set
        assert isinstance(summary.get_start_time_iso(), str)

    def test_mark_failed_uses_typed_context(self):
        """Test that mark_failed creates properly typed context."""
        execution = ModelCliExecution(command_name="test-command")

        # Mark as failed with reason
        execution.mark_failed("Test failure reason")

        # Verify the failure reason is stored as typed context
        failure_context = execution.get_context("failure_reason")
        assert isinstance(failure_context, ModelCliExecutionContext)
        assert failure_context.key == "failure_reason"
        assert failure_context.value == "Test failure reason"
        assert failure_context.context_type == "error"
        assert failure_context.source == "system"


class TestNewModelValidation:
    """Test validation of the new typed models."""

    def test_command_option_validation(self):
        """Test ModelCliCommandOption validation."""
        # Valid option
        option = ModelCliCommandOption(
            name="--count", value=5, description="Number of items"
        )
        assert option.name == "--count"
        assert option.value == 5
        assert not option.is_flag

        # Flag option
        flag = ModelCliCommandOption(name="--verbose", value=True, is_flag=True)
        assert flag.is_boolean_flag() is True

    def test_input_data_validation(self):
        """Test ModelCliExecutionInputData validation."""
        # Path value
        input_data = ModelCliExecutionInputData(
            key="config_path", value=Path("/config/app.yaml"), data_type="path"
        )
        assert input_data.is_path_value() is True
        assert str(input_data.value) == "/config/app.yaml"

        # UUID value
        test_uuid = uuid4()
        uuid_data = ModelCliExecutionInputData(
            key="session_id", value=test_uuid, data_type="uuid"
        )
        assert uuid_data.is_uuid_value() is True

    def test_execution_context_validation(self):
        """Test ModelCliExecutionContext validation."""
        # Datetime value
        now = datetime.now(UTC)
        context = ModelCliExecutionContext(
            key="created_at", value=now, context_type="timestamp"
        )
        assert context.is_datetime_value() is True
        assert context.value == now

        # Value update updates timestamp
        old_updated_at = context.updated_at
        context.update_value("new_value")
        assert context.value == "new_value"
        assert context.updated_at > old_updated_at

    def test_execution_summary_validation(self):
        """Test ModelCliExecutionSummary validation."""
        test_id = uuid4()
        start_time = datetime.now(UTC)

        summary = ModelCliExecutionSummary(
            execution_id=test_id,
            command_name="test-cmd",
            status=EnumExecutionStatus.SUCCESS,
            start_time=start_time,
            elapsed_ms=1500,
            retry_count=0,
            is_dry_run=False,
            is_test_execution=True,
            progress_percentage=100.0,
        )

        assert summary.execution_id == test_id
        assert summary.get_duration_seconds() == 1.5
        assert summary.is_successful() is True
        assert summary.get_start_time_iso() == start_time.isoformat()
        assert summary.get_end_time_iso() is None  # Not completed
