"""
Tests for ModelCliExecutionCore.

Validates CLI execution core model functionality including
execution state management, timing, progress tracking, and command handling.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.cli.model_cli_execution_core import ModelCliExecutionCore


@pytest.mark.unit
class TestModelCliExecutionCoreBasic:
    """Test basic CLI execution core functionality."""

    def test_minimal_core_creation(self):
        """Test creating core with minimal required fields."""
        command_name_id = uuid4()
        core = ModelCliExecutionCore(command_name_id=command_name_id)

        assert core.command_name_id == command_name_id
        assert core.command_display_name is None
        assert core.command_args == []
        assert core.command_options == {}
        assert core.target_node_id is None
        assert core.target_node_display_name is None
        assert core.target_path is None
        assert core.status == EnumExecutionStatus.PENDING
        assert core.current_phase is None
        assert isinstance(core.start_time, datetime)
        assert core.end_time is None
        assert core.progress_percentage == 0.0
        assert isinstance(core.execution_id, UUID)

    def test_full_core_creation(self):
        """Test creating core with all fields."""
        command_name_id = uuid4()
        target_node_id = uuid4()
        execution_id = uuid4()
        start_time = datetime.now(UTC)
        target_path = Path("/fake/test/path")

        core = ModelCliExecutionCore(
            execution_id=execution_id,
            command_name_id=command_name_id,
            command_display_name="test_command",
            command_args=["arg1", "arg2"],
            target_node_id=target_node_id,
            target_node_display_name="test_node",
            target_path=target_path,
            status=EnumExecutionStatus.RUNNING,
            current_phase=EnumExecutionPhase.PROCESSING,
            start_time=start_time,
            progress_percentage=50.0,
        )

        assert core.execution_id == execution_id
        assert core.command_name_id == command_name_id
        assert core.command_display_name == "test_command"
        assert core.command_args == ["arg1", "arg2"]
        assert core.target_node_id == target_node_id
        assert core.target_node_display_name == "test_node"
        assert core.target_path == target_path
        assert core.status == EnumExecutionStatus.RUNNING
        assert core.current_phase == EnumExecutionPhase.PROCESSING
        assert core.start_time == start_time
        assert core.progress_percentage == 50.0


@pytest.mark.unit
class TestModelCliExecutionCoreGetters:
    """Test getter methods."""

    def test_get_command_name_with_display_name(self):
        """Test getting command name when display name is set."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_display_name="my_command",
        )

        assert core.get_command_name() == "my_command"

    def test_get_command_name_without_display_name(self):
        """Test getting command name when display name is not set."""
        command_id = uuid4()
        core = ModelCliExecutionCore(command_name_id=command_id)

        name = core.get_command_name()
        assert "command_" in name
        assert str(command_id)[:8] in name

    def test_get_target_node_id(self):
        """Test getting target node ID."""
        target_id = uuid4()
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            target_node_id=target_id,
        )

        assert core.get_target_node_id() == target_id

    def test_get_target_node_id_none(self):
        """Test getting target node ID when not set."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.get_target_node_id() is None

    def test_get_target_node_name(self):
        """Test getting target node name."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            target_node_display_name="test_node",
        )

        assert core.get_target_node_name() == "test_node"

    def test_get_target_node_name_none(self):
        """Test getting target node name when not set."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.get_target_node_name() is None


@pytest.mark.unit
class TestModelCliExecutionCoreTiming:
    """Test timing-related methods."""

    def test_get_elapsed_ms_with_end_time(self):
        """Test getting elapsed time in ms with end time set."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(seconds=2.5)

        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
        )

        elapsed = core.get_elapsed_ms()
        assert 2400 <= elapsed <= 2600  # ~2500ms with some tolerance

    def test_get_elapsed_ms_without_end_time(self):
        """Test getting elapsed time in ms without end time set."""
        start_time = datetime.now(UTC) - timedelta(seconds=1)

        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            start_time=start_time,
        )

        elapsed = core.get_elapsed_ms()
        assert elapsed >= 900  # At least 900ms

    def test_get_elapsed_seconds(self):
        """Test getting elapsed time in seconds."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(seconds=3)

        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
        )

        elapsed = core.get_elapsed_seconds()
        assert 2.9 <= elapsed <= 3.1  # ~3 seconds with tolerance


@pytest.mark.unit
class TestModelCliExecutionCoreStatus:
    """Test status checking methods."""

    def test_is_completed_true(self):
        """Test is_completed when end_time is set."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            end_time=datetime.now(UTC),
        )

        assert core.is_completed() is True

    def test_is_completed_false(self):
        """Test is_completed when end_time is not set."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.is_completed() is False

    def test_is_running_true(self):
        """Test is_running when status is RUNNING and no end_time."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.RUNNING,
        )

        assert core.is_running() is True

    def test_is_running_false_with_end_time(self):
        """Test is_running false when end_time is set."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.RUNNING,
            end_time=datetime.now(UTC),
        )

        assert core.is_running() is False

    def test_is_running_false_different_status(self):
        """Test is_running false when status is not RUNNING."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.PENDING,
        )

        assert core.is_running() is False

    def test_is_pending_true(self):
        """Test is_pending when status is PENDING."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.PENDING,
        )

        assert core.is_pending() is True

    def test_is_pending_false(self):
        """Test is_pending when status is not PENDING."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.RUNNING,
        )

        assert core.is_pending() is False

    def test_is_failed_true(self):
        """Test is_failed when status is FAILED."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.FAILED,
        )

        assert core.is_failed() is True

    def test_is_failed_false(self):
        """Test is_failed when status is not FAILED."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.SUCCESS,
        )

        assert core.is_failed() is False

    def test_is_successful_with_success_status(self):
        """Test is_successful when status is SUCCESS."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.SUCCESS,
        )

        assert core.is_successful() is True

    def test_is_successful_with_completed_status(self):
        """Test is_successful when status is COMPLETED."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.COMPLETED,
        )

        assert core.is_successful() is True

    def test_is_successful_false(self):
        """Test is_successful when status is neither SUCCESS nor COMPLETED."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.FAILED,
        )

        assert core.is_successful() is False


@pytest.mark.unit
class TestModelCliExecutionCoreStateManagement:
    """Test state management methods."""

    def test_mark_started(self):
        """Test marking execution as started."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        original_start_time = core.start_time

        core.mark_started()

        assert core.status == EnumExecutionStatus.RUNNING
        assert core.start_time >= original_start_time

    def test_mark_completed(self):
        """Test marking execution as completed."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.RUNNING,
        )

        assert core.end_time is None

        core.mark_completed()

        assert core.end_time is not None
        assert core.status == EnumExecutionStatus.SUCCESS

    def test_mark_completed_does_not_change_non_running_status(self):
        """Test mark_completed does not change status if not RUNNING."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            status=EnumExecutionStatus.PENDING,
        )

        core.mark_completed()

        assert core.end_time is not None
        assert core.status == EnumExecutionStatus.PENDING  # Status unchanged

    def test_mark_failed(self):
        """Test marking execution as failed."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.end_time is None

        core.mark_failed()

        assert core.status == EnumExecutionStatus.FAILED
        assert core.end_time is not None

    def test_mark_cancelled(self):
        """Test marking execution as cancelled."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.end_time is None

        core.mark_cancelled()

        assert core.status == EnumExecutionStatus.CANCELLED
        assert core.end_time is not None

    def test_set_phase(self):
        """Test setting execution phase."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        core.set_phase(EnumExecutionPhase.PROCESSING)

        assert core.current_phase == EnumExecutionPhase.PROCESSING

    def test_set_progress(self):
        """Test setting progress percentage."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        core.set_progress(75.5)

        assert core.progress_percentage == 75.5

    def test_set_progress_clamps_to_minimum(self):
        """Test set_progress clamps to minimum (0)."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        core.set_progress(-10.0)

        assert core.progress_percentage == 0.0

    def test_set_progress_clamps_to_maximum(self):
        """Test set_progress clamps to maximum (100)."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        core.set_progress(150.0)

        assert core.progress_percentage == 100.0


@pytest.mark.unit
class TestModelCliExecutionCoreFactoryMethods:
    """Test factory methods."""

    def test_create_simple_minimal(self):
        """Test create_simple with minimal parameters."""
        core = ModelCliExecutionCore.create_simple("test_command")

        assert core.command_display_name == "test_command"
        assert isinstance(core.command_name_id, UUID)
        assert core.target_node_id is None
        assert core.target_node_display_name is None

    def test_create_simple_with_target(self):
        """Test create_simple with target node."""
        target_id = uuid4()
        core = ModelCliExecutionCore.create_simple(
            "test_command",
            target_node_id=target_id,
            target_node_name="test_target",
        )

        assert core.command_display_name == "test_command"
        assert core.target_node_id == target_id
        assert core.target_node_display_name == "test_target"

    def test_create_simple_generates_consistent_uuid(self):
        """Test that create_simple generates same UUID for same command name."""
        core1 = ModelCliExecutionCore.create_simple("same_command")
        core2 = ModelCliExecutionCore.create_simple("same_command")

        assert core1.command_name_id == core2.command_name_id


@pytest.mark.unit
class TestModelCliExecutionCoreProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialize method (Serializable protocol)."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_display_name="test",
            status=EnumExecutionStatus.RUNNING,
        )

        data = core.serialize()

        assert isinstance(data, dict)
        assert "command_display_name" in data
        assert "status" in data

    def test_get_name(self):
        """Test get_name method (Nameable protocol)."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        name = core.get_name()

        assert "ModelCliExecutionCore" in name

    def test_set_name(self):
        """Test set_name method (Nameable protocol)."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        # Should not raise exception
        core.set_name("test_name")

    def test_validate_instance(self):
        """Test validate_instance method (ProtocolValidatable protocol)."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        result = core.validate_instance()

        assert result is True


@pytest.mark.unit
class TestModelCliExecutionCoreSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_display_name="test",
            progress_percentage=50.0,
        )

        data = core.model_dump()

        assert data["command_display_name"] == "test"
        assert data["progress_percentage"] == 50.0

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_display_name="test_command",
            command_args=["arg1", "arg2"],
            status=EnumExecutionStatus.RUNNING,
            progress_percentage=75.0,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionCore.model_validate(data)

        assert restored.command_display_name == original.command_display_name
        assert restored.command_args == original.command_args
        assert restored.status == original.status
        assert restored.progress_percentage == original.progress_percentage


@pytest.mark.unit
class TestModelCliExecutionCoreEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_command_args(self):
        """Test with empty command args."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_args=[],
        )

        assert core.command_args == []

    def test_many_command_args(self):
        """Test with many command args."""
        args = [f"arg{i}" for i in range(100)]
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_args=args,
        )

        assert len(core.command_args) == 100

    def test_empty_command_options(self):
        """Test with empty command options."""
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            command_options={},
        )

        assert core.command_options == {}

    def test_progress_boundary_values(self):
        """Test progress at boundary values."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        # Test 0%
        core.set_progress(0.0)
        assert core.progress_percentage == 0.0

        # Test 100%
        core.set_progress(100.0)
        assert core.progress_percentage == 100.0

    def test_multiple_status_changes(self):
        """Test multiple status changes."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.is_pending()

        core.mark_started()
        assert core.is_running()

        core.mark_completed()
        assert core.is_successful()
        assert core.is_completed()

    def test_status_change_from_pending_to_failed(self):
        """Test status change from pending directly to failed."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        assert core.is_pending()

        core.mark_failed()
        assert core.is_failed()
        assert core.is_completed()

    def test_all_execution_phases(self):
        """Test setting all execution phases."""
        core = ModelCliExecutionCore(command_name_id=uuid4())

        for phase in EnumExecutionPhase:
            core.set_phase(phase)
            assert core.current_phase == phase

    def test_target_path_with_absolute_path(self):
        """Test target path with absolute path."""
        path = Path("/absolute/path/to/file.txt")
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            target_path=path,
        )

        assert core.target_path == path

    def test_target_path_with_relative_path(self):
        """Test target path with relative path."""
        path = Path("relative/path/file.txt")
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            target_path=path,
        )

        assert core.target_path == path

    def test_zero_elapsed_time(self):
        """Test elapsed time when start and end are very close."""
        now = datetime.now(UTC)
        core = ModelCliExecutionCore(
            command_name_id=uuid4(),
            start_time=now,
            end_time=now,
        )

        elapsed = core.get_elapsed_ms()
        assert elapsed >= 0
        assert elapsed < 100  # Should be very small
