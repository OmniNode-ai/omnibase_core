"""
Unit tests for ModelResultSummary.

Tests result summary model with protocol implementations and validation.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.cli.model_result_summary import ModelResultSummary


@pytest.mark.unit
class TestModelResultSummaryBasics:
    """Test basic initialization and validation."""

    def test_successful_execution_minimal(self):
        """Test model for successful execution with minimal data."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.execution_id == execution_id
        assert summary.command == "test_command"
        assert summary.target_node == "node1"
        assert summary.success is True
        assert summary.exit_code == 0
        assert summary.duration_ms == 100.0
        assert summary.retry_count == 0
        assert summary.has_errors is False
        assert summary.has_warnings is False

    def test_failed_execution_with_errors(self):
        """Test model for failed execution with errors."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="failing_command",
            target_node="node2",
            success=False,
            exit_code=1,
            duration_ms=250.0,
            retry_count=3,
            has_errors=True,
            has_warnings=True,
            error_count=5,
            warning_count=2,
            critical_error_count=1,
        )

        assert summary.success is False
        assert summary.exit_code == 1
        assert summary.retry_count == 3
        assert summary.has_errors is True
        assert summary.has_warnings is True
        assert summary.error_count == 5
        assert summary.warning_count == 2
        assert summary.critical_error_count == 1

    def test_missing_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResultSummary()  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "execution_id" in error_str or "command" in error_str

    def test_none_target_node(self):
        """Test with None target_node."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="global_command",
            target_node=None,
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.target_node is None


@pytest.mark.unit
class TestModelResultSummaryExecutionStatus:
    """Test execution status scenarios."""

    def test_successful_no_retries(self):
        """Test successful execution with no retries."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="quick_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=50.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.success is True
        assert summary.retry_count == 0
        assert summary.has_errors is False

    def test_successful_with_retries(self):
        """Test successful execution after retries."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="retry_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=500.0,
            retry_count=2,
            has_errors=False,
            has_warnings=True,
            error_count=0,
            warning_count=3,
            critical_error_count=0,
        )

        assert summary.success is True
        assert summary.retry_count == 2
        assert summary.has_warnings is True

    def test_failed_no_retries(self):
        """Test failed execution with no retries."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="failing_task",
            target_node="node2",
            success=False,
            exit_code=1,
            duration_ms=100.0,
            retry_count=0,
            has_errors=True,
            has_warnings=False,
            error_count=1,
            warning_count=0,
            critical_error_count=1,
        )

        assert summary.success is False
        assert summary.retry_count == 0
        assert summary.has_errors is True

    def test_failed_max_retries(self):
        """Test failed execution after max retries."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="persistent_failure",
            target_node="node3",
            success=False,
            exit_code=1,
            duration_ms=1000.0,
            retry_count=5,
            has_errors=True,
            has_warnings=True,
            error_count=10,
            warning_count=5,
            critical_error_count=2,
        )

        assert summary.success is False
        assert summary.retry_count == 5
        assert summary.error_count == 10


@pytest.mark.unit
class TestModelResultSummaryErrorCounts:
    """Test error and warning counting."""

    def test_no_errors_or_warnings(self):
        """Test with no errors or warnings."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="clean_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.error_count == 0
        assert summary.warning_count == 0
        assert summary.critical_error_count == 0

    def test_only_warnings(self):
        """Test with only warnings."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="warning_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=True,
            error_count=0,
            warning_count=10,
            critical_error_count=0,
        )

        assert summary.has_warnings is True
        assert summary.warning_count == 10
        assert summary.has_errors is False

    def test_errors_and_warnings(self):
        """Test with both errors and warnings."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="mixed_task",
            target_node="node2",
            success=False,
            exit_code=1,
            duration_ms=200.0,
            retry_count=1,
            has_errors=True,
            has_warnings=True,
            error_count=3,
            warning_count=7,
            critical_error_count=1,
        )

        assert summary.has_errors is True
        assert summary.has_warnings is True
        assert summary.error_count == 3
        assert summary.warning_count == 7
        assert summary.critical_error_count == 1

    def test_only_critical_errors(self):
        """Test with only critical errors."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="critical_failure",
            target_node="node3",
            success=False,
            exit_code=2,
            duration_ms=50.0,
            retry_count=0,
            has_errors=True,
            has_warnings=False,
            error_count=5,
            warning_count=0,
            critical_error_count=5,
        )

        assert summary.critical_error_count == 5
        assert summary.error_count == 5


@pytest.mark.unit
class TestModelResultSummaryProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialization to dictionary."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        data = summary.serialize()

        assert isinstance(data, dict)
        assert "execution_id" in data
        assert "command" in data
        assert "success" in data
        assert data["command"] == "test_command"

    def test_get_name_default(self):
        """Test default name generation."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        name = summary.get_name()

        assert "ModelResultSummary" in name
        assert "Unnamed" in name

    def test_set_name_no_field(self):
        """Test set_name when no name field exists."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        # Should not raise
        summary.set_name("test_summary")

        # Name still returns default
        assert "Unnamed" in summary.get_name()

    def test_validate_instance(self):
        """Test instance validation."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        result = summary.validate_instance()

        assert result is True


@pytest.mark.unit
class TestModelResultSummaryEdgeCases:
    """Test edge cases and boundary values."""

    def test_zero_duration(self):
        """Test with zero duration."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="instant_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=0.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.duration_ms == 0.0

    def test_large_duration(self):
        """Test with very large duration."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="long_task",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=3600000.0,  # 1 hour
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        assert summary.duration_ms == 3600000.0

    def test_various_exit_codes(self):
        """Test with various exit codes."""
        execution_id = uuid4()

        # Exit code 0 (success)
        summary1 = ModelResultSummary(
            execution_id=execution_id,
            command="cmd",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )
        assert summary1.exit_code == 0

        # Exit code 1 (general error)
        summary2 = ModelResultSummary(
            execution_id=uuid4(),
            command="cmd",
            target_node="node1",
            success=False,
            exit_code=1,
            duration_ms=100.0,
            retry_count=0,
            has_errors=True,
            has_warnings=False,
            error_count=1,
            warning_count=0,
            critical_error_count=0,
        )
        assert summary2.exit_code == 1

        # Exit code 127 (command not found)
        summary3 = ModelResultSummary(
            execution_id=uuid4(),
            command="cmd",
            target_node="node1",
            success=False,
            exit_code=127,
            duration_ms=100.0,
            retry_count=0,
            has_errors=True,
            has_warnings=False,
            error_count=1,
            warning_count=0,
            critical_error_count=1,
        )
        assert summary3.exit_code == 127

    def test_large_retry_count(self):
        """Test with large retry count."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="retry_heavy_task",
            target_node="node1",
            success=False,
            exit_code=1,
            duration_ms=5000.0,
            retry_count=100,
            has_errors=True,
            has_warnings=True,
            error_count=100,
            warning_count=50,
            critical_error_count=10,
        )

        assert summary.retry_count == 100

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
            unknown_field="value",  # type: ignore[call-arg]
        )

        assert summary.command == "test_command"
        assert not hasattr(summary, "unknown_field")

    def test_validate_assignment(self):
        """Test validate_assignment config."""
        execution_id = uuid4()

        summary = ModelResultSummary(
            execution_id=execution_id,
            command="test_command",
            target_node="node1",
            success=True,
            exit_code=0,
            duration_ms=100.0,
            retry_count=0,
            has_errors=False,
            has_warnings=False,
            error_count=0,
            warning_count=0,
            critical_error_count=0,
        )

        # Should allow valid assignment
        summary.duration_ms = 200.0
        assert summary.duration_ms == 200.0

        summary.retry_count = 3
        assert summary.retry_count == 3

        summary.success = False
        assert summary.success is False
