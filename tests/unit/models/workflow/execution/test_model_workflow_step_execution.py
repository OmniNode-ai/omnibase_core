"""Tests for ModelWorkflowStepExecution.

Tests the production model at:
src/omnibase_core/models/workflow/execution/model_workflow_step_execution.py

Validates step_name length constraints using MAX_NAME_LENGTH (255) constant.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.enums.enum_workflow_execution import (
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.workflow.execution.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)

pytestmark = pytest.mark.unit


class TestModelWorkflowStepExecution:
    """Test suite for ModelWorkflowStepExecution."""

    def test_create_minimal_valid_step(self) -> None:
        """Test creating a step with minimal required fields."""
        step = ModelWorkflowStepExecution(
            step_name="test_step",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.step_name == "test_step"
        assert step.execution_mode == EnumExecutionMode.SEQUENTIAL
        assert step.state == EnumWorkflowState.PENDING

    def test_step_name_minimum_length(self) -> None:
        """Test step_name with minimum length (1 character)."""
        step = ModelWorkflowStepExecution(
            step_name="x",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.step_name == "x"
        assert len(step.step_name) == 1

    def test_step_name_at_max_length(self) -> None:
        """Test step_name at exactly MAX_NAME_LENGTH (255) characters."""
        max_name = "x" * MAX_NAME_LENGTH
        step = ModelWorkflowStepExecution(
            step_name=max_name,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert len(step.step_name) == MAX_NAME_LENGTH
        assert len(step.step_name) == 255

    def test_step_name_empty_rejected(self) -> None:
        """Test that empty step_name is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStepExecution(
                step_name="",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
        assert "step_name" in str(exc_info.value)

    def test_step_name_exceeds_max_length_rejected(self) -> None:
        """Test that step_name exceeding MAX_NAME_LENGTH (255) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStepExecution(
                step_name="x" * (MAX_NAME_LENGTH + 1),  # 256 characters
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )
        error_str = str(exc_info.value)
        assert "step_name" in error_str

    def test_step_name_length_bounds(self) -> None:
        """Comprehensive test of step_name length constraints (min=1, max=255)."""
        # Valid at minimum
        step = ModelWorkflowStepExecution(
            step_name="a",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.step_name == "a"

        # Valid at maximum
        step = ModelWorkflowStepExecution(
            step_name="b" * MAX_NAME_LENGTH,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert len(step.step_name) == MAX_NAME_LENGTH

        # Invalid: empty
        with pytest.raises(ValidationError):
            ModelWorkflowStepExecution(
                step_name="",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        # Invalid: exceeds max
        with pytest.raises(ValidationError):
            ModelWorkflowStepExecution(
                step_name="c" * (MAX_NAME_LENGTH + 1),  # 256 characters
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

    def test_step_id_auto_generated(self) -> None:
        """Test that step_id is auto-generated as UUID."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.step_id is not None
        # UUID is valid (no exception from accessing it)
        assert str(step.step_id) != ""

    def test_step_id_can_be_provided(self) -> None:
        """Test that custom step_id can be provided."""
        custom_id = uuid4()
        step = ModelWorkflowStepExecution(
            step_id=custom_id,
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.step_id == custom_id

    def test_default_state_is_pending(self) -> None:
        """Test that default state is PENDING."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.state == EnumWorkflowState.PENDING

    def test_all_execution_modes(self) -> None:
        """Test all valid execution modes."""
        for mode in EnumExecutionMode:
            step = ModelWorkflowStepExecution(
                step_name="test",
                execution_mode=mode,
            )
            assert step.execution_mode == mode

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes=True works for ORM-style objects."""

        class MockObject:
            step_id = uuid4()
            step_name = "orm_step"
            execution_mode = EnumExecutionMode.PARALLEL
            thunks = []
            condition = None
            condition_function = None
            timeout_ms = 30000
            retry_count = 0
            state = EnumWorkflowState.PENDING
            started_at = None
            completed_at = None
            error = None
            results = []

        step = ModelWorkflowStepExecution.model_validate(MockObject())
        assert step.step_name == "orm_step"
        assert step.execution_mode == EnumExecutionMode.PARALLEL

    def test_model_allows_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored (extra='ignore')."""
        # This should not raise - extra fields are ignored
        step = ModelWorkflowStepExecution.model_validate(
            {
                "step_name": "test",
                "execution_mode": EnumExecutionMode.SEQUENTIAL,
                "unknown_field": "value",  # Should be ignored
            }
        )
        assert step.step_name == "test"
        assert not hasattr(step, "unknown_field")

    def test_timeout_ms_default_value(self) -> None:
        """Test that timeout_ms has appropriate default."""
        from omnibase_core.constants import TIMEOUT_DEFAULT_MS

        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.timeout_ms == TIMEOUT_DEFAULT_MS

    def test_retry_count_default_zero(self) -> None:
        """Test that retry_count defaults to 0."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.retry_count == 0

    def test_retry_count_valid_range(self) -> None:
        """Test retry_count within valid range (0-10)."""
        for count in [0, 5, 10]:
            step = ModelWorkflowStepExecution(
                step_name="test",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                retry_count=count,
            )
            assert step.retry_count == count

    def test_retry_count_exceeds_max_rejected(self) -> None:
        """Test that retry_count > 10 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStepExecution(
                step_name="test",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                retry_count=11,
            )
        assert "retry_count" in str(exc_info.value)

    def test_retry_count_negative_rejected(self) -> None:
        """Test that negative retry_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStepExecution(
                step_name="test",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                retry_count=-1,
            )
        assert "retry_count" in str(exc_info.value)

    def test_thunks_default_empty_list(self) -> None:
        """Test that thunks defaults to empty list."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.thunks == []

    def test_results_default_empty_list(self) -> None:
        """Test that results defaults to empty list."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.results == []

    def test_timestamps_initially_none(self) -> None:
        """Test that started_at and completed_at are initially None."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.started_at is None
        assert step.completed_at is None

    def test_error_initially_none(self) -> None:
        """Test that error is initially None."""
        step = ModelWorkflowStepExecution(
            step_name="test",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        assert step.error is None
