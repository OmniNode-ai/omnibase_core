"""Tests for ModelProgressCore."""

import pytest

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_status_message import EnumStatusMessage
from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.infrastructure.progress.model_progress_core import (
    ModelProgressCore,
)


class TestModelProgressCoreInstantiation:
    """Tests for ModelProgressCore instantiation."""

    def test_default_initialization(self):
        """Test default initialization."""
        progress = ModelProgressCore()
        assert progress.percentage == 0.0
        assert progress.current_step == 0
        assert progress.total_steps == 1
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION
        assert progress.status_message == EnumStatusMessage.PENDING

    def test_create_with_total_steps(self):
        """Test creating with custom total steps."""
        progress = ModelProgressCore(total_steps=10)
        assert progress.total_steps == 10
        assert progress.current_step == 0

    def test_create_with_initial_percentage(self):
        """Test creating with initial percentage."""
        progress = ModelProgressCore(percentage=50.0)
        assert progress.percentage == 50.0

    def test_create_with_phase(self):
        """Test creating with specific phase."""
        progress = ModelProgressCore(current_phase=EnumExecutionPhase.EXECUTION)
        assert progress.current_phase == EnumExecutionPhase.EXECUTION


class TestModelProgressCoreValidation:
    """Tests for ModelProgressCore validation."""

    def test_percentage_min_validation(self):
        """Test percentage minimum validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelProgressCore(percentage=-1.0)

    def test_percentage_max_validation(self):
        """Test percentage maximum validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelProgressCore(percentage=101.0)

    def test_current_step_negative_validation(self):
        """Test current_step negative validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelProgressCore(current_step=-1)

    def test_total_steps_zero_validation(self):
        """Test total_steps zero validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelProgressCore(total_steps=0)

    def test_current_step_exceeds_total(self):
        """Test validation when current_step exceeds total_steps."""
        # The validator should raise OnexError when current_step > total_steps
        with pytest.raises(OnexError) as exc_info:
            ModelProgressCore(total_steps=5, current_step=10)
        assert "cannot exceed total steps" in str(exc_info.value)


class TestModelProgressCoreProperties:
    """Tests for ModelProgressCore computed properties."""

    def test_is_completed_true(self):
        """Test is_completed when at 100%."""
        progress = ModelProgressCore(percentage=100.0)
        assert progress.is_completed is True

    def test_is_completed_false(self):
        """Test is_completed when below 100%."""
        progress = ModelProgressCore(percentage=99.9)
        assert progress.is_completed is False

    def test_is_started_true(self):
        """Test is_started when above 0%."""
        progress = ModelProgressCore(percentage=0.1)
        assert progress.is_started is True

    def test_is_started_false(self):
        """Test is_started when at 0%."""
        progress = ModelProgressCore(percentage=0.0)
        assert progress.is_started is False

    def test_completion_ratio(self):
        """Test completion_ratio calculation."""
        progress = ModelProgressCore(percentage=50.0)
        assert progress.completion_ratio == 0.5


class TestModelProgressCorePercentageUpdates:
    """Tests for ModelProgressCore percentage updates."""

    def test_update_percentage(self):
        """Test update_percentage method."""
        progress = ModelProgressCore()
        progress.update_percentage(75.0)
        assert progress.percentage == 75.0

    def test_update_percentage_clamped_max(self):
        """Test update_percentage clamps to 100%."""
        progress = ModelProgressCore()
        progress.update_percentage(150.0)
        assert progress.percentage == 100.0

    def test_update_percentage_clamped_min(self):
        """Test update_percentage clamps to 0%."""
        progress = ModelProgressCore()
        progress.update_percentage(-50.0)
        assert progress.percentage == 0.0

    def test_percentage_from_steps(self):
        """Test automatic percentage calculation from steps."""
        progress = ModelProgressCore(total_steps=10, current_step=5)
        assert progress.percentage == 50.0


class TestModelProgressCoreStepUpdates:
    """Tests for ModelProgressCore step updates."""

    def test_update_step(self):
        """Test update_step method."""
        progress = ModelProgressCore(total_steps=10)
        progress.update_step(3)
        assert progress.current_step == 3
        assert progress.percentage == 30.0

    def test_update_step_clamped_max(self):
        """Test update_step clamps to total_steps."""
        progress = ModelProgressCore(total_steps=5)
        progress.update_step(10)
        assert progress.current_step == 5
        assert progress.percentage == 100.0

    def test_update_step_clamped_min(self):
        """Test update_step clamps to 0."""
        progress = ModelProgressCore(total_steps=10)
        progress.update_step(-5)
        assert progress.current_step == 0

    def test_increment_step(self):
        """Test increment_step method."""
        progress = ModelProgressCore(total_steps=10)
        progress.increment_step()
        assert progress.current_step == 1
        progress.increment_step(2)
        assert progress.current_step == 3

    def test_increment_step_with_amount(self):
        """Test increment_step with custom amount."""
        progress = ModelProgressCore(total_steps=10)
        progress.increment_step(5)
        assert progress.current_step == 5
        assert progress.percentage == 50.0


class TestModelProgressCorePhaseManagement:
    """Tests for ModelProgressCore phase management."""

    def test_set_phase(self):
        """Test set_phase method."""
        progress = ModelProgressCore()
        progress.set_phase(EnumExecutionPhase.EXECUTION, phase_percentage=25.0)
        assert progress.current_phase == EnumExecutionPhase.EXECUTION
        assert progress.phase_percentage == 25.0

    def test_set_phase_without_percentage(self):
        """Test set_phase without phase_percentage."""
        progress = ModelProgressCore()
        progress.set_phase(EnumExecutionPhase.VALIDATION)
        assert progress.current_phase == EnumExecutionPhase.VALIDATION
        assert progress.phase_percentage == 0.0

    def test_update_phase_percentage(self):
        """Test update_phase_percentage method."""
        progress = ModelProgressCore(current_phase=EnumExecutionPhase.EXECUTION)
        progress.update_phase_percentage(50.0)
        assert progress.phase_percentage == 50.0

    def test_update_phase_percentage_clamped_max(self):
        """Test update_phase_percentage clamps to 100%."""
        progress = ModelProgressCore()
        progress.update_phase_percentage(150.0)
        assert progress.phase_percentage == 100.0

    def test_update_phase_percentage_clamped_min(self):
        """Test update_phase_percentage clamps to 0%."""
        progress = ModelProgressCore()
        progress.update_phase_percentage(-50.0)
        assert progress.phase_percentage == 0.0


class TestModelProgressCoreStatusManagement:
    """Tests for ModelProgressCore status management."""

    def test_set_status(self):
        """Test set_status method."""
        progress = ModelProgressCore()
        progress.set_status(
            EnumStatusMessage.PROCESSING, detailed_info="Processing data"
        )
        assert progress.status_message == EnumStatusMessage.PROCESSING
        assert progress.detailed_info == "Processing data"

    def test_set_status_without_detailed_info(self):
        """Test set_status without detailed info."""
        progress = ModelProgressCore()
        progress.set_status(EnumStatusMessage.COMPLETED)
        assert progress.status_message == EnumStatusMessage.COMPLETED
        assert progress.detailed_info == ""

    def test_set_status_preserves_existing_info(self):
        """Test set_status preserves info when not provided."""
        progress = ModelProgressCore(detailed_info="Initial info")
        progress.set_status(EnumStatusMessage.PROCESSING)
        assert progress.detailed_info == "Initial info"


class TestModelProgressCoreReset:
    """Tests for ModelProgressCore reset functionality."""

    def test_reset(self):
        """Test reset method."""
        progress = ModelProgressCore(
            percentage=75.0,
            current_step=8,
            total_steps=10,
            current_phase=EnumExecutionPhase.EXECUTION,
            phase_percentage=50.0,
            status_message=EnumStatusMessage.PROCESSING,
            detailed_info="Running task",
        )
        progress.reset()
        assert progress.percentage == 0.0
        assert progress.current_step == 0
        assert progress.phase_percentage == 0.0
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION
        assert progress.status_message == EnumStatusMessage.PENDING
        assert progress.detailed_info == ""


class TestModelProgressCoreFactoryMethods:
    """Tests for ModelProgressCore factory methods."""

    def test_create_simple(self):
        """Test create_simple factory method."""
        progress = ModelProgressCore.create_simple(total_steps=5)
        assert progress.total_steps == 5
        assert progress.percentage == 0.0
        assert progress.current_step == 0

    def test_create_simple_default(self):
        """Test create_simple with default total_steps."""
        progress = ModelProgressCore.create_simple()
        assert progress.total_steps == 1

    def test_create_phased(self):
        """Test create_phased factory method."""
        phases = [
            EnumExecutionPhase.INITIALIZATION,
            EnumExecutionPhase.EXECUTION,
            EnumExecutionPhase.VALIDATION,
        ]
        progress = ModelProgressCore.create_phased(phases, total_steps=10)
        assert progress.total_steps == 10
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION

    def test_create_phased_empty_phases(self):
        """Test create_phased with empty phases list."""
        progress = ModelProgressCore.create_phased([], total_steps=5)
        assert progress.current_phase == EnumExecutionPhase.INITIALIZATION


class TestModelProgressCoreProtocols:
    """Tests for ModelProgressCore protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        progress = ModelProgressCore()
        result = progress.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        progress = ModelProgressCore()
        result = progress.configure()
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize method."""
        progress = ModelProgressCore(percentage=50.0, current_step=5, total_steps=10)
        data = progress.serialize()
        assert isinstance(data, dict)
        assert data["percentage"] == 50.0
        assert data["current_step"] == 5
        assert data["total_steps"] == 10


class TestModelProgressCoreEdgeCases:
    """Tests for ModelProgressCore edge cases."""

    def test_detailed_info_max_length(self):
        """Test detailed_info max length validation."""
        long_string = "x" * 2001
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelProgressCore(detailed_info=long_string)

    def test_detailed_info_at_max_length(self):
        """Test detailed_info at exactly max length."""
        max_string = "x" * 2000
        progress = ModelProgressCore(detailed_info=max_string)
        assert len(progress.detailed_info) == 2000

    def test_percentage_at_boundary_100(self):
        """Test percentage exactly at 100%."""
        progress = ModelProgressCore(percentage=100.0)
        assert progress.is_completed is True

    def test_percentage_just_below_100(self):
        """Test percentage just below 100%."""
        progress = ModelProgressCore(percentage=99.99)
        assert progress.is_completed is False

    def test_step_calculation_with_one_step(self):
        """Test percentage calculation with single step."""
        progress = ModelProgressCore(total_steps=1, current_step=1)
        assert progress.percentage == 100.0
