"""Tests for ModelProgress (composed model)."""

from datetime import timedelta

import pytest

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_status_message import EnumStatusMessage
from omnibase_core.models.infrastructure.model_progress import ModelProgress


@pytest.mark.unit
class TestModelProgressInstantiation:
    """Tests for ModelProgress instantiation."""

    def test_default_initialization(self):
        """Test default initialization creates all components."""
        progress = ModelProgress()
        assert progress.core is not None
        assert progress.timing is not None
        assert progress.milestones is not None
        assert progress.metrics is not None

    def test_initialization_syncs_components(self):
        """Test that initialization syncs components."""
        progress = ModelProgress()
        assert progress.percentage == 0.0
        assert progress.current_step == 0


@pytest.mark.unit
class TestModelProgressCorePropertiesAccess:
    """Tests for ModelProgress core properties access through composition."""

    def test_percentage_property_read(self):
        """Test reading percentage through composed property."""
        progress = ModelProgress()
        assert progress.percentage == progress.core.percentage

    def test_percentage_property_write(self):
        """Test writing percentage through composed property."""
        progress = ModelProgress()
        progress.percentage = 50.0
        assert progress.core.percentage == 50.0

    def test_current_step_property_read(self):
        """Test reading current_step."""
        progress = ModelProgress()
        assert progress.current_step == progress.core.current_step

    def test_current_step_property_write(self):
        """Test writing current_step."""
        progress = ModelProgress()
        progress.total_steps = 10  # Set total_steps first to allow step updates
        progress.current_step = 5
        assert progress.core.current_step == 5

    def test_total_steps_property_read(self):
        """Test reading total_steps."""
        progress = ModelProgress()
        assert progress.total_steps == progress.core.total_steps

    def test_total_steps_property_write(self):
        """Test writing total_steps."""
        progress = ModelProgress()
        progress.total_steps = 10
        assert progress.core.total_steps == 10


@pytest.mark.unit
class TestModelProgressTimingPropertiesAccess:
    """Tests for ModelProgress timing properties access."""

    def test_start_time_property(self):
        """Test accessing start_time."""
        progress = ModelProgress()
        assert progress.start_time is not None

    def test_last_update_time_property(self):
        """Test accessing last_update_time."""
        progress = ModelProgress()
        assert progress.last_update_time is not None

    def test_elapsed_time_property(self):
        """Test accessing elapsed_time."""
        progress = ModelProgress()
        elapsed = progress.elapsed_time
        assert isinstance(elapsed, timedelta)

    def test_elapsed_seconds_property(self):
        """Test accessing elapsed_seconds."""
        progress = ModelProgress()
        elapsed = progress.elapsed_seconds
        assert elapsed >= 0.0


@pytest.mark.unit
class TestModelProgressStatusProperties:
    """Tests for ModelProgress status properties."""

    def test_is_completed_property(self):
        """Test is_completed property."""
        progress = ModelProgress()
        assert progress.is_completed is False
        progress.percentage = 100.0
        assert progress.is_completed is True

    def test_is_started_property(self):
        """Test is_started property."""
        progress = ModelProgress()
        assert progress.is_started is False
        progress.percentage = 1.0
        assert progress.is_started is True

    def test_current_phase_property(self):
        """Test current_phase property."""
        progress = ModelProgress()
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION

    def test_status_message_property(self):
        """Test status_message property."""
        progress = ModelProgress()
        assert progress.status_message == EnumStatusMessage.PENDING


@pytest.mark.unit
class TestModelProgressUpdateMethods:
    """Tests for ModelProgress update methods."""

    def test_update_percentage_syncs_components(self):
        """Test update_percentage syncs all components."""
        progress = ModelProgress()
        progress.update_percentage(50.0)
        assert progress.core.percentage == 50.0

    def test_update_step_syncs_components(self):
        """Test update_step syncs all components."""
        progress = ModelProgress()
        progress.total_steps = 10
        progress.update_step(5)
        assert progress.core.current_step == 5

    def test_increment_step_syncs_components(self):
        """Test increment_step syncs all components."""
        progress = ModelProgress()
        progress.total_steps = 10
        progress.increment_step(3)
        assert progress.core.current_step == 3

    def test_set_phase(self):
        """Test set_phase method."""
        progress = ModelProgress()
        progress.set_phase(EnumExecutionPhase.EXECUTION, phase_percentage=25.0)
        assert progress.current_phase == EnumExecutionPhase.EXECUTION
        assert progress.phase_percentage == 25.0

    def test_update_phase_percentage(self):
        """Test update_phase_percentage method."""
        progress = ModelProgress()
        progress.update_phase_percentage(75.0)
        assert progress.phase_percentage == 75.0

    def test_set_status(self):
        """Test set_status method."""
        progress = ModelProgress()
        progress.set_status(EnumStatusMessage.PROCESSING, detailed_info="Test info")
        assert progress.status_message == EnumStatusMessage.PROCESSING
        assert progress.detailed_info == "Test info"


@pytest.mark.unit
class TestModelProgressMilestones:
    """Tests for ModelProgress milestone methods."""

    def test_add_milestone(self):
        """Test add_milestone method."""
        progress = ModelProgress()
        progress.add_milestone("halfway", 50.0)
        next_milestone = progress.get_next_milestone()
        assert next_milestone is not None

    def test_remove_milestone(self):
        """Test remove_milestone method."""
        progress = ModelProgress()
        progress.add_milestone("test", 50.0)
        result = progress.remove_milestone("test")
        assert result is True

    def test_get_next_milestone(self):
        """Test get_next_milestone method."""
        progress = ModelProgress()
        progress.add_milestone("first", 25.0)
        progress.add_milestone("second", 75.0)
        next_milestone = progress.get_next_milestone()
        assert next_milestone is not None


@pytest.mark.unit
class TestModelProgressMetricsMethods:
    """Tests for ModelProgress metrics methods."""

    def test_add_custom_metric(self):
        """Test add_custom_metric method."""
        progress = ModelProgress()
        # add_custom_metric accepts plain values
        progress.add_custom_metric("test_key", "test")
        assert progress.metrics.get_metrics_count() > 0

    def test_add_tag(self):
        """Test add_tag method."""
        progress = ModelProgress()
        progress.add_tag("important")
        assert "important" in progress.tags

    def test_remove_tag(self):
        """Test remove_tag method."""
        progress = ModelProgress()
        progress.add_tag("test")
        result = progress.remove_tag("test")
        assert result is True

    def test_custom_metrics_property(self):
        """Test custom_metrics property access."""
        progress = ModelProgress()
        assert progress.custom_metrics is not None

    def test_tags_property(self):
        """Test tags property access."""
        progress = ModelProgress()
        assert isinstance(progress.tags, list)


@pytest.mark.unit
class TestModelProgressReset:
    """Tests for ModelProgress reset functionality."""

    def test_reset_resets_all_components(self):
        """Test reset method resets all components."""
        progress = ModelProgress()
        progress.percentage = 75.0
        progress.add_tag("test")
        progress.add_milestone("test", 50.0)
        progress.reset()
        assert progress.percentage == 0.0
        assert len(progress.tags) == 0


@pytest.mark.unit
class TestModelProgressSummary:
    """Tests for ModelProgress summary methods."""

    def test_get_summary(self):
        """Test get_summary method."""
        progress = ModelProgress()
        progress.percentage = 50.0
        summary = progress.get_summary()
        assert "percentage" in summary
        assert "current_step" in summary
        assert "total_steps" in summary
        assert "elapsed_seconds" in summary


@pytest.mark.unit
class TestModelProgressFactoryMethods:
    """Tests for ModelProgress factory methods."""

    def test_create_simple(self):
        """Test create_simple factory method."""
        progress = ModelProgress.create_simple(total_steps=5)
        assert progress.total_steps == 5

    def test_create_with_milestones(self):
        """Test create_with_milestones factory method."""
        milestones = {"start": 0.0, "middle": 50.0, "end": 100.0}
        progress = ModelProgress.create_with_milestones(milestones, total_steps=10)
        assert progress.total_steps == 10

    def test_create_phased(self):
        """Test create_phased factory method."""
        phases = [
            EnumExecutionPhase.INITIALIZATION,
            EnumExecutionPhase.EXECUTION,
            EnumExecutionPhase.VALIDATION,
        ]
        progress = ModelProgress.create_phased(phases, total_steps=10)
        assert progress.total_steps == 10
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION


@pytest.mark.unit
class TestModelProgressProtocols:
    """Tests for ModelProgress protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        progress = ModelProgress()
        result = progress.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        progress = ModelProgress()
        result = progress.configure()
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize method."""
        progress = ModelProgress()
        data = progress.serialize()
        assert isinstance(data, dict)
        assert "core" in data
        assert "timing" in data
        assert "milestones" in data
        assert "metrics" in data


@pytest.mark.unit
class TestModelProgressEdgeCases:
    """Tests for ModelProgress edge cases."""

    def test_percentage_updates_sync(self):
        """Test that percentage updates sync timing and milestones."""
        progress = ModelProgress()
        progress.add_milestone("test", 50.0)
        progress.percentage = 60.0
        # Verify components are synced
        assert progress.core.percentage == 60.0

    def test_step_updates_sync(self):
        """Test that step updates sync percentage and timing."""
        progress = ModelProgress()
        progress.total_steps = 10
        progress.current_step = 5
        # Should update percentage to 50%
        assert progress.percentage == 50.0

    def test_total_steps_updates_sync(self):
        """Test that total_steps updates sync percentage calculation."""
        progress = ModelProgress()
        progress.total_steps = 10
        progress.current_step = 5
        # Should calculate percentage to 50%
        assert progress.percentage == 50.0
