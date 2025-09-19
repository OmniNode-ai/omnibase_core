"""
Unit tests for ModelCliExecution.

Tests all aspects of the CLI execution model including:
- Model instantiation and validation
- Field validation and type checking
- Serialization/deserialization
- Business logic and state management
- Edge cases and error conditions
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.models.core.model_cli_execution import ModelCliExecution


class TestModelCliExecution:
    """Test cases for ModelCliExecution."""

    def test_model_instantiation_minimal_data(self):
        """Test that model can be instantiated with minimal required data."""
        execution = ModelCliExecution(command_name="test_command")

        assert execution.command_name == "test_command"
        assert isinstance(execution.execution_id, UUID)  # Should be UUID type
        assert str(execution.execution_id)  # Should convert to valid string
        assert execution.command_args == []
        assert execution.command_options == {}
        assert execution.status == EnumExecutionStatus.PENDING
        assert execution.progress_percentage == 0.0
        assert execution.max_retries == 0
        assert execution.retry_count == 0
        assert execution.capture_output is True
        assert execution.output_format == EnumOutputFormat.TEXT

    def test_model_instantiation_with_all_fields(self):
        """Test model instantiation with all fields provided."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(minutes=5)

        execution = ModelCliExecution(
            execution_id=UUID("12345678-1234-5678-9abc-123456789abc"),
            command_name="deploy",
            command_args=["--env", "prod"],
            command_options={"force": True, "timeout": 300},
            target_node_name="app_node",
            target_path="/app/config",
            working_directory="/workspace",
            environment_vars={"ENV": "production"},
            is_dry_run=True,
            is_test_execution=True,
            is_debug_enabled=True,
            is_trace_enabled=True,
            is_verbose=True,
            start_time=start_time,
            end_time=end_time,
            status=EnumExecutionStatus.COMPLETED,
            current_phase=EnumExecutionPhase.EXECUTION,
            progress_percentage=100.0,
            timeout_seconds=300,
            max_memory_mb=512,
            max_retries=3,
            retry_count=1,
            user_id=UUID("11111111-2222-3333-4444-555555555555"),
            session_id=UUID("66666666-7777-8888-9999-aaaaaaaaaaaa"),
            input_data={"config": "value"},
            output_format=EnumOutputFormat.JSON,
            capture_output=False,
            custom_context={"metadata": "test"},
            execution_tags=["production", "deployment"],
        )

        assert execution.execution_id == UUID("12345678-1234-5678-9abc-123456789abc")
        assert execution.command_name == "deploy"
        assert execution.command_args == ["--env", "prod"]
        assert execution.command_options == {"force": True, "timeout": 300}
        assert execution.target_node_name == "app_node"
        assert str(execution.target_path) == "/app/config"
        assert str(execution.working_directory) == "/workspace"
        assert execution.environment_vars == {"ENV": "production"}
        assert execution.is_dry_run is True
        assert execution.is_test_execution is True
        assert execution.is_debug_enabled is True
        assert execution.is_trace_enabled is True
        assert execution.is_verbose is True
        assert execution.start_time == start_time
        assert execution.end_time == end_time
        assert execution.status == EnumExecutionStatus.COMPLETED
        assert execution.current_phase == EnumExecutionPhase.EXECUTION
        assert execution.progress_percentage == 100.0
        assert execution.timeout_seconds == 300
        assert execution.max_memory_mb == 512
        assert execution.max_retries == 3
        assert execution.retry_count == 1
        assert execution.user_id == UUID("11111111-2222-3333-4444-555555555555")
        assert execution.session_id == UUID("66666666-7777-8888-9999-aaaaaaaaaaaa")
        assert execution.input_data == {"config": "value"}
        assert execution.output_format == EnumOutputFormat.JSON
        assert execution.capture_output is False
        assert execution.custom_context == {"metadata": "test"}
        assert execution.execution_tags == ["production", "deployment"]

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing command_name
        with pytest.raises(ValidationError) as exc_info:
            ModelCliExecution()
        assert "command_name" in str(exc_info.value)

        # Empty command_name should be valid (no min_length constraint)
        execution = ModelCliExecution(command_name="")
        assert execution.command_name == ""

    def test_progress_percentage_validation(self):
        """Test that progress_percentage is validated within range."""
        # Valid range
        execution = ModelCliExecution(command_name="test", progress_percentage=50.0)
        assert execution.progress_percentage == 50.0

        # Minimum boundary
        execution = ModelCliExecution(command_name="test", progress_percentage=0.0)
        assert execution.progress_percentage == 0.0

        # Maximum boundary
        execution = ModelCliExecution(command_name="test", progress_percentage=100.0)
        assert execution.progress_percentage == 100.0

        # Below minimum
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", progress_percentage=-1.0)

        # Above maximum
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", progress_percentage=101.0)

    def test_timeout_seconds_validation(self):
        """Test that timeout_seconds is validated as positive integer."""
        # Valid value
        execution = ModelCliExecution(command_name="test", timeout_seconds=300)
        assert execution.timeout_seconds == 300

        # Minimum valid value
        execution = ModelCliExecution(command_name="test", timeout_seconds=1)
        assert execution.timeout_seconds == 1

        # Zero should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", timeout_seconds=0)

        # Negative should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", timeout_seconds=-1)

    def test_max_memory_mb_validation(self):
        """Test that max_memory_mb is validated as positive integer."""
        # Valid value
        execution = ModelCliExecution(command_name="test", max_memory_mb=512)
        assert execution.max_memory_mb == 512

        # Minimum valid value
        execution = ModelCliExecution(command_name="test", max_memory_mb=1)
        assert execution.max_memory_mb == 1

        # Zero should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", max_memory_mb=0)

        # Negative should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", max_memory_mb=-1)

    def test_retry_validation(self):
        """Test that retry fields are validated as non-negative integers."""
        # Valid values
        execution = ModelCliExecution(command_name="test", max_retries=3, retry_count=1)
        assert execution.max_retries == 3
        assert execution.retry_count == 1

        # Zero values should be valid
        execution = ModelCliExecution(command_name="test", max_retries=0, retry_count=0)
        assert execution.max_retries == 0
        assert execution.retry_count == 0

        # Negative max_retries should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", max_retries=-1)

        # Negative retry_count should be invalid
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", retry_count=-1)

    def test_default_factory_fields(self):
        """Test that fields with default factories work correctly."""
        execution1 = ModelCliExecution(command_name="test1")
        execution2 = ModelCliExecution(command_name="test2")

        # Each instance should have unique IDs
        assert execution1.execution_id != execution2.execution_id

        # Each instance should have independent collections
        execution1.command_args.append("arg1")
        execution1.command_options["key1"] = "value1"
        execution1.environment_vars["VAR1"] = "val1"
        execution1.input_data["input1"] = "data1"
        execution1.custom_context["ctx1"] = "context1"
        execution1.execution_tags.append("tag1")

        # execution2 should not be affected
        assert execution2.command_args == []
        assert execution2.command_options == {}
        assert execution2.environment_vars == {}
        assert execution2.input_data == {}
        assert execution2.custom_context == {}
        assert execution2.execution_tags == []

    def test_get_command_name_method(self):
        """Test the get_command_name method."""
        execution = ModelCliExecution(command_name="deploy")
        assert execution.get_command_name() == "deploy"

    def test_get_target_node_name_method(self):
        """Test the get_target_node_name method."""
        # With target node
        execution = ModelCliExecution(
            command_name="deploy", target_node_name="app_node"
        )
        assert execution.get_target_node_name() == "app_node"

        # Without target node
        execution = ModelCliExecution(command_name="deploy")
        assert execution.get_target_node_name() is None

    def test_elapsed_time_methods(self):
        """Test elapsed time calculation methods."""
        start_time = datetime.now(UTC)
        execution = ModelCliExecution(command_name="test", start_time=start_time)

        # Test with end_time set
        end_time = start_time + timedelta(seconds=5.5)
        execution.end_time = end_time

        assert execution.get_elapsed_ms() == 5500
        assert execution.get_elapsed_seconds() == 5.5

        # Test without end_time (should use current time)
        execution.end_time = None
        elapsed_ms = execution.get_elapsed_ms()
        elapsed_seconds = execution.get_elapsed_seconds()

        assert elapsed_ms >= 0
        assert elapsed_seconds >= 0.0
        assert abs(elapsed_seconds - (elapsed_ms / 1000.0)) < 0.001

    def test_status_check_methods(self):
        """Test status checking methods."""
        execution = ModelCliExecution(command_name="test")

        # Test is_completed
        assert execution.is_completed() is False
        execution.end_time = datetime.now(UTC)
        assert execution.is_completed() is True

        # Reset for other tests
        execution.end_time = None

        # Test is_running
        execution.status = EnumExecutionStatus.RUNNING
        assert execution.is_running() is True
        execution.end_time = datetime.now(UTC)
        assert execution.is_running() is False

        # Reset for other tests
        execution.end_time = None

        # Test is_pending
        execution.status = EnumExecutionStatus.PENDING
        assert execution.is_pending() is True
        execution.status = EnumExecutionStatus.RUNNING
        assert execution.is_pending() is False

        # Test is_failed
        execution.status = EnumExecutionStatus.FAILED
        assert execution.is_failed() is True
        execution.status = EnumExecutionStatus.SUCCESS
        assert execution.is_failed() is False

        # Test is_successful
        execution.status = EnumExecutionStatus.SUCCESS
        assert execution.is_successful() is True
        execution.status = EnumExecutionStatus.FAILED
        assert execution.is_successful() is False

    def test_is_timed_out_method(self):
        """Test the is_timed_out method."""
        start_time = datetime.now(UTC) - timedelta(seconds=10)
        execution = ModelCliExecution(command_name="test", start_time=start_time)

        # No timeout set
        assert execution.is_timed_out() is False

        # Timeout not exceeded
        execution.timeout_seconds = 20
        assert execution.is_timed_out() is False

        # Timeout exceeded
        execution.timeout_seconds = 5
        assert execution.is_timed_out() is True

    def test_mark_started_method(self):
        """Test the mark_started method."""
        execution = ModelCliExecution(command_name="test")
        original_start_time = execution.start_time

        execution.mark_started()

        assert execution.status == EnumExecutionStatus.RUNNING
        assert execution.start_time >= original_start_time

    def test_mark_completed_method(self):
        """Test the mark_completed method."""
        execution = ModelCliExecution(command_name="test")
        execution.status = EnumExecutionStatus.RUNNING

        execution.mark_completed()

        assert execution.status == EnumExecutionStatus.SUCCESS
        assert execution.end_time is not None
        assert execution.is_completed() is True

        # Test with non-running status
        execution2 = ModelCliExecution(command_name="test2")
        execution2.status = EnumExecutionStatus.PENDING
        execution2.mark_completed()

        assert (
            execution2.status == EnumExecutionStatus.PENDING
        )  # Should not change to success
        assert execution2.end_time is not None

    def test_mark_failed_method(self):
        """Test the mark_failed method."""
        execution = ModelCliExecution(command_name="test")

        # Without reason
        execution.mark_failed()

        assert execution.status == EnumExecutionStatus.FAILED
        assert execution.end_time is not None
        assert execution.is_completed() is True

        # With reason
        execution2 = ModelCliExecution(command_name="test2")
        execution2.mark_failed("Connection timeout")

        assert execution2.status == EnumExecutionStatus.FAILED
        assert execution2.end_time is not None
        assert execution2.custom_context["failure_reason"] == "Connection timeout"

    def test_mark_cancelled_method(self):
        """Test the mark_cancelled method."""
        execution = ModelCliExecution(command_name="test")

        execution.mark_cancelled()

        assert execution.status == EnumExecutionStatus.CANCELLED
        assert execution.end_time is not None
        assert execution.is_completed() is True

    def test_set_phase_method(self):
        """Test the set_phase method."""
        execution = ModelCliExecution(command_name="test")

        execution.set_phase(EnumExecutionPhase.INITIALIZATION)
        assert execution.current_phase == EnumExecutionPhase.INITIALIZATION

        execution.set_phase(EnumExecutionPhase.EXECUTION)
        assert execution.current_phase == EnumExecutionPhase.EXECUTION

    def test_set_progress_method(self):
        """Test the set_progress method."""
        execution = ModelCliExecution(command_name="test")

        # Normal value
        execution.set_progress(75.5)
        assert execution.progress_percentage == 75.5

        # Value below minimum (should clamp to 0)
        execution.set_progress(-10.0)
        assert execution.progress_percentage == 0.0

        # Value above maximum (should clamp to 100)
        execution.set_progress(150.0)
        assert execution.progress_percentage == 100.0

    def test_increment_retry_method(self):
        """Test the increment_retry method."""
        execution = ModelCliExecution(command_name="test", max_retries=2)

        # First retry
        assert execution.increment_retry() is True
        assert execution.retry_count == 1

        # Second retry
        assert execution.increment_retry() is True
        assert execution.retry_count == 2

        # Third retry (exceeds max)
        assert execution.increment_retry() is False
        assert execution.retry_count == 3

    def test_add_tag_method(self):
        """Test the add_tag method."""
        execution = ModelCliExecution(command_name="test")

        execution.add_tag("production")
        assert "production" in execution.execution_tags

        execution.add_tag("deployment")
        assert "deployment" in execution.execution_tags
        assert len(execution.execution_tags) == 2

        # Adding duplicate should not create duplicate
        execution.add_tag("production")
        assert execution.execution_tags.count("production") == 1
        assert len(execution.execution_tags) == 2

    def test_context_methods(self):
        """Test add_context and get_context methods."""
        execution = ModelCliExecution(command_name="test")

        # Add context
        execution.add_context("key1", "value1")
        execution.add_context("key2", 42)

        # Get context
        assert execution.get_context("key1") == "value1"
        assert execution.get_context("key2") == 42
        assert execution.get_context("nonexistent") is None
        assert execution.get_context("nonexistent", "default") == "default"

    def test_input_data_methods(self):
        """Test add_input_data and get_input_data methods."""
        execution = ModelCliExecution(command_name="test")

        # Add input data
        execution.add_input_data("config", {"setting": "value"})
        execution.add_input_data("parameters", ["param1", "param2"])

        # Get input data
        assert execution.get_input_data("config") == {"setting": "value"}
        assert execution.get_input_data("parameters") == ["param1", "param2"]
        assert execution.get_input_data("nonexistent") is None
        assert execution.get_input_data("nonexistent", []) == []

    def test_get_summary_method(self):
        """Test the get_summary method."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(seconds=5)

        execution = ModelCliExecution(
            command_name="deploy",
            target_node_name="app_node",
            start_time=start_time,
            end_time=end_time,
            status=EnumExecutionStatus.COMPLETED,
            current_phase=EnumExecutionPhase.EXECUTION,
            progress_percentage=100.0,
            retry_count=1,
            is_dry_run=True,
            is_test_execution=True,
        )

        summary = execution.get_summary()

        assert summary["command_name"] == "deploy"
        assert summary["target_node_name"] == "app_node"
        assert summary["status"] == EnumExecutionStatus.COMPLETED
        assert summary["start_time"] == start_time.isoformat()
        assert summary["end_time"] == end_time.isoformat()
        assert summary["elapsed_ms"] == 5000
        assert summary["retry_count"] == 1
        assert summary["is_dry_run"] is True
        assert summary["is_test_execution"] is True
        assert summary["progress_percentage"] == 100.0
        assert summary["current_phase"] == EnumExecutionPhase.EXECUTION
        assert "execution_id" in summary

        # Test with no end_time
        execution.end_time = None
        summary = execution.get_summary()
        assert summary["end_time"] is None

    def test_factory_methods(self):
        """Test factory methods."""
        # create_simple
        execution = ModelCliExecution.create_simple("deploy", "app_node")
        assert execution.command_name == "deploy"
        assert execution.target_node_name == "app_node"
        assert execution.is_dry_run is False
        assert execution.is_test_execution is False

        # create_dry_run
        execution = ModelCliExecution.create_dry_run("deploy", "app_node")
        assert execution.command_name == "deploy"
        assert execution.target_node_name == "app_node"
        assert execution.is_dry_run is True
        assert execution.is_test_execution is False

        # create_test_execution
        execution = ModelCliExecution.create_test_execution("deploy", "app_node")
        assert execution.command_name == "deploy"
        assert execution.target_node_name == "app_node"
        assert execution.is_dry_run is False
        assert execution.is_test_execution is True

        # Factory methods with None target
        execution = ModelCliExecution.create_simple("deploy")
        assert execution.command_name == "deploy"
        assert execution.target_node_name is None

    def test_model_serialization(self):
        """Test model serialization to dict."""
        execution = ModelCliExecution(
            command_name="test_command",
            command_args=["arg1", "arg2"],
            command_options={"option": "value"},
            status=EnumExecutionStatus.RUNNING,
            progress_percentage=50.0,
        )

        data = execution.model_dump()

        assert data["command_name"] == "test_command"
        assert data["command_args"] == ["arg1", "arg2"]
        assert data["command_options"] == {"option": "value"}
        assert data["status"] == EnumExecutionStatus.RUNNING
        assert data["progress_percentage"] == 50.0
        assert "execution_id" in data
        assert "start_time" in data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        start_time = datetime.now(UTC)
        data = {
            "execution_id": "12345678-1234-5678-9abc-123456789abc",
            "command_name": "deploy",
            "command_args": ["--env", "prod"],
            "command_options": {"force": True},
            "status": "completed",
            "start_time": start_time.isoformat(),
            "progress_percentage": 100.0,
            "timeout_seconds": 300,
            "max_retries": 3,
            "retry_count": 1,
        }

        execution = ModelCliExecution.model_validate(data)

        assert execution.execution_id == UUID("12345678-1234-5678-9abc-123456789abc")
        assert execution.command_name == "deploy"
        assert execution.command_args == ["--env", "prod"]
        assert execution.command_options == {"force": True}
        assert execution.status == EnumExecutionStatus.COMPLETED
        assert execution.progress_percentage == 100.0
        assert execution.timeout_seconds == 300
        assert execution.max_retries == 3
        assert execution.retry_count == 1

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        execution = ModelCliExecution(
            command_name="backup",
            target_node_name="data_node",
            status=EnumExecutionStatus.RUNNING,
        )

        # Serialize to JSON
        json_str = execution.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        execution_from_json = ModelCliExecution.model_validate_json(json_str)

        assert execution_from_json.command_name == execution.command_name
        assert execution_from_json.target_node_name == execution.target_node_name
        assert execution_from_json.status == execution.status
        assert execution_from_json.execution_id == execution.execution_id

    def test_model_equality(self):
        """Test model equality comparison."""
        execution_id = UUID("12345678-1234-5678-9abc-123456789abc")
        start_time = datetime.now(UTC)

        execution1 = ModelCliExecution(
            execution_id=execution_id, command_name="deploy", start_time=start_time
        )

        execution2 = ModelCliExecution(
            execution_id=execution_id, command_name="deploy", start_time=start_time
        )

        execution3 = ModelCliExecution(
            execution_id=UUID("87654321-4321-8765-9abc-987654321abc"),
            command_name="deploy",
            start_time=start_time,
        )

        assert execution1 == execution2
        assert execution1 != execution3


class TestModelCliExecutionEdgeCases:
    """Test edge cases and error conditions for ModelCliExecution."""

    def test_invalid_field_types(self):
        """Test behavior with invalid field types."""
        # Non-string command_name
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name=123)

        # Non-list command_args
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", command_args="not_a_list")

        # Non-dict command_options
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", command_options="not_a_dict")

        # Non-bool flags should be converted by Pydantic
        execution = ModelCliExecution(command_name="test", is_dry_run="true")
        assert execution.is_dry_run is True

        # Non-datetime start_time
        with pytest.raises(ValidationError):
            ModelCliExecution(command_name="test", start_time="not_a_datetime")

    def test_datetime_handling(self):
        """Test datetime field handling."""
        # Valid datetime
        dt = datetime.now(UTC)
        execution = ModelCliExecution(command_name="test", start_time=dt)
        assert execution.start_time == dt

        # Valid end_time
        end_dt = dt + timedelta(minutes=5)
        execution.end_time = end_dt
        assert execution.end_time == end_dt

    def test_large_values(self):
        """Test handling of large values."""
        # Large timeout
        execution = ModelCliExecution(command_name="test", timeout_seconds=999999999)
        assert execution.timeout_seconds == 999999999

        # Large memory limit
        execution = ModelCliExecution(command_name="test", max_memory_mb=999999999)
        assert execution.max_memory_mb == 999999999

        # Large retry counts
        execution = ModelCliExecution(
            command_name="test", max_retries=999999999, retry_count=999999999
        )
        assert execution.max_retries == 999999999
        assert execution.retry_count == 999999999

    def test_empty_collections(self):
        """Test behavior with empty collections."""
        execution = ModelCliExecution(
            command_name="test",
            command_args=[],
            command_options={},
            environment_vars={},
            input_data={},
            custom_context={},
            execution_tags=[],
        )

        assert execution.command_args == []
        assert execution.command_options == {}
        assert execution.environment_vars == {}
        assert execution.input_data == {}
        assert execution.custom_context == {}
        assert execution.execution_tags == []

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        execution = ModelCliExecution(
            command_name="tést_çommänd",
            command_args=["ärg1", "🚀"],
            target_node_name="node_ñ",
            working_directory="/päth/with/ünicode",
            user_id=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        )

        assert execution.command_name == "tést_çommänd"
        assert execution.command_args == ["ärg1", "🚀"]
        assert execution.target_node_name == "node_ñ"
        assert str(execution.working_directory) == "/päth/with/ünicode"
        assert execution.user_id == UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_none_values_for_optional_fields(self):
        """Test explicit None values for optional fields."""
        execution = ModelCliExecution(
            command_name="test",
            target_node_name=None,
            target_path=None,
            working_directory=None,
            end_time=None,
            current_phase=None,
            timeout_seconds=None,
            max_memory_mb=None,
            user_id=None,
            session_id=None,
            unit=None,
            data_source=None,
            forecast_points=None,
            confidence_interval=None,
            anomaly_points=None,
            anomaly_threshold=None,
        )

        assert execution.target_node_name is None
        assert execution.target_path is None
        assert execution.working_directory is None
        assert execution.end_time is None
        assert execution.current_phase is None
        assert execution.timeout_seconds is None
        assert execution.max_memory_mb is None
        assert execution.user_id is None
        assert execution.session_id is None

    def test_edge_case_retry_logic(self):
        """Test edge cases in retry logic."""
        # Max retries = 0
        execution = ModelCliExecution(command_name="test", max_retries=0)
        assert execution.increment_retry() is False
        assert execution.retry_count == 1

        # Max retries = retry count initially
        execution2 = ModelCliExecution(
            command_name="test", max_retries=2, retry_count=2
        )
        assert execution2.increment_retry() is False
        assert execution2.retry_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
