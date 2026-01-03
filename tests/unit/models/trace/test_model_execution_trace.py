"""
Unit tests for ModelExecutionTrace.

Tests comprehensive execution trace functionality including:
- Model instantiation and validation
- Steps ordering preservation
- Duration calculation
- Failed steps retrieval
- Success determination
- Correlation and dispatch ID handling
- Status enum values
- Utility methods (get_step_count, get_steps_by_kind, etc.)
- Serialization and deserialization
- Edge cases and error conditions
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.trace import (
    ModelExecutionTrace,
    ModelExecutionTraceStep,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_trace_data() -> dict:
    """Minimal required data for creating an execution trace."""
    return {
        "correlation_id": uuid4(),
        "run_id": uuid4(),
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
        "status": EnumExecutionStatus.SUCCESS,
    }


@pytest.fixture
def full_trace_data() -> dict:
    """Complete data for creating an execution trace with all fields."""
    return {
        "trace_id": uuid4(),
        "correlation_id": uuid4(),
        "dispatch_id": uuid4(),
        "run_id": uuid4(),
        "started_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "ended_at": datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC),
        "status": EnumExecutionStatus.SUCCESS,
        "steps": [],
    }


@pytest.fixture
def sample_step_success() -> ModelExecutionTraceStep:
    """Create a successful trace step."""
    return ModelExecutionTraceStep(
        step_id="step-001",
        step_kind="handler",
        name="fetch_data",
        start_ts=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        end_ts=datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC),
        duration_ms=2000.0,
        status="success",
    )


@pytest.fixture
def sample_step_effect() -> ModelExecutionTraceStep:
    """Create an effect_call trace step."""
    return ModelExecutionTraceStep(
        step_id="step-002",
        step_kind="effect_call",
        name="transform_data",
        start_ts=datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC),
        end_ts=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
        duration_ms=3000.0,
        status="success",
    )


@pytest.fixture
def sample_step_failed() -> ModelExecutionTraceStep:
    """Create a failed trace step."""
    return ModelExecutionTraceStep(
        step_id="step-003",
        step_kind="effect_call",
        name="write_output",
        start_ts=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
        end_ts=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
        duration_ms=1000.0,
        status="failure",
        error_summary="Write operation failed: disk full",
    )


@pytest.fixture
def sample_step_skipped() -> ModelExecutionTraceStep:
    """Create a skipped trace step."""
    return ModelExecutionTraceStep(
        step_id="step-004",
        step_kind="hook",
        name="optional_validation",
        start_ts=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
        end_ts=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
        duration_ms=0.0,
        status="skipped",
    )


# ============================================================================
# Test: Trace Creation with Required Fields
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceInstantiation:
    """Test cases for ModelExecutionTrace instantiation."""

    def test_trace_creation_with_required_fields(
        self, minimal_trace_data: dict
    ) -> None:
        """Test trace creation with only required fields."""
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert isinstance(trace.trace_id, UUID)
        assert isinstance(trace.correlation_id, UUID)
        assert isinstance(trace.run_id, UUID)
        assert trace.started_at is not None
        assert trace.ended_at is not None
        assert trace.status == EnumExecutionStatus.SUCCESS
        # Optional fields should have default values
        assert trace.dispatch_id is None
        assert trace.steps == []

    def test_trace_creation_with_all_fields(self, full_trace_data: dict) -> None:
        """Test trace creation with all fields populated."""
        trace = ModelExecutionTrace(**full_trace_data)

        assert isinstance(trace.trace_id, UUID)
        assert isinstance(trace.correlation_id, UUID)
        assert isinstance(trace.dispatch_id, UUID)
        assert isinstance(trace.run_id, UUID)
        assert trace.started_at == datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert trace.ended_at == datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        assert trace.status == EnumExecutionStatus.SUCCESS
        assert trace.steps == []


# ============================================================================
# Test: Trace Creation with Steps
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceWithSteps:
    """Test trace creation with steps."""

    def test_trace_creation_with_steps(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test trace creation with multiple steps."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert len(trace.steps) == 2
        assert trace.steps[0].name == "fetch_data"
        assert trace.steps[1].name == "transform_data"

    def test_trace_empty_steps_list(self, minimal_trace_data: dict) -> None:
        """Test trace with explicitly empty steps list."""
        minimal_trace_data["steps"] = []
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.steps == []
        assert len(trace.steps) == 0


# ============================================================================
# Test: Steps Ordering Preserved
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepsOrdering:
    """Test that steps ordering is preserved."""

    def test_trace_steps_ordering_preserved(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test that steps maintain insertion order."""
        steps = [sample_step_success, sample_step_effect, sample_step_failed]
        minimal_trace_data["steps"] = steps
        trace = ModelExecutionTrace(**minimal_trace_data)

        # Verify order is preserved
        assert trace.steps[0].step_id == "step-001"
        assert trace.steps[0].name == "fetch_data"
        assert trace.steps[1].step_id == "step-002"
        assert trace.steps[1].name == "transform_data"
        assert trace.steps[2].step_id == "step-003"
        assert trace.steps[2].name == "write_output"

    def test_trace_steps_ordering_after_serialization(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test that steps ordering is preserved after JSON roundtrip."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        # Serialize and deserialize
        json_str = trace.model_dump_json()
        restored = ModelExecutionTrace.model_validate_json(json_str)

        # Verify order is still preserved
        assert restored.steps[0].name == "fetch_data"
        assert restored.steps[1].name == "transform_data"


# ============================================================================
# Test: Duration Calculation
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceDurationCalculation:
    """Test duration calculation methods."""

    def test_trace_get_duration_ms_calculation(self, minimal_trace_data: dict) -> None:
        """Test duration calculation from started_at and ended_at."""
        minimal_trace_data["started_at"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_trace_data["ended_at"] = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        trace = ModelExecutionTrace(**minimal_trace_data)

        duration = trace.get_duration_ms()
        # 10 seconds = 10000 milliseconds
        assert duration == 10000.0

    def test_trace_get_duration_ms_with_milliseconds(
        self, minimal_trace_data: dict
    ) -> None:
        """Test duration calculation includes milliseconds."""
        minimal_trace_data["started_at"] = datetime(2025, 1, 1, 12, 0, 0, 0, tzinfo=UTC)
        minimal_trace_data["ended_at"] = datetime(
            2025, 1, 1, 12, 0, 0, 500000, tzinfo=UTC
        )
        trace = ModelExecutionTrace(**minimal_trace_data)

        duration = trace.get_duration_ms()
        assert duration == 500.0  # 500ms

    def test_trace_get_duration_seconds(self, minimal_trace_data: dict) -> None:
        """Test get_duration_seconds method."""
        minimal_trace_data["started_at"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_trace_data["ended_at"] = datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC)
        trace = ModelExecutionTrace(**minimal_trace_data)

        duration = trace.get_duration_seconds()
        assert duration == 5.0

    def test_trace_get_duration_ms_zero_duration(
        self, minimal_trace_data: dict
    ) -> None:
        """Test duration calculation when start and end are the same."""
        same_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_trace_data["started_at"] = same_time
        minimal_trace_data["ended_at"] = same_time
        trace = ModelExecutionTrace(**minimal_trace_data)

        duration = trace.get_duration_ms()
        assert duration == 0.0


# ============================================================================
# Test: Get Failed Steps
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceGetFailedSteps:
    """Test get_failed_steps method."""

    def test_trace_get_failed_steps(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test retrieving only failed steps."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_failed]
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace = ModelExecutionTrace(**minimal_trace_data)

        failed_steps = trace.get_failed_steps()

        assert len(failed_steps) == 1
        assert failed_steps[0].name == "write_output"
        assert failed_steps[0].status == "failure"

    def test_trace_get_failed_steps_no_failures(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_failed_steps returns empty list when no failures."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        failed_steps = trace.get_failed_steps()

        assert len(failed_steps) == 0
        assert failed_steps == []

    def test_trace_get_failed_steps_multiple_failures(
        self,
        minimal_trace_data: dict,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test get_failed_steps returns all failed steps."""
        # Create another failed step
        another_failed = ModelExecutionTraceStep(
            step_id="step-005",
            step_kind="hook",
            name="another_failure",
            start_ts=datetime(2025, 1, 1, 12, 0, 7, tzinfo=UTC),
            end_ts=datetime(2025, 1, 1, 12, 0, 8, tzinfo=UTC),
            duration_ms=1000.0,
            status="failure",
            error_summary="Another error",
        )
        minimal_trace_data["steps"] = [sample_step_failed, another_failed]
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace = ModelExecutionTrace(**minimal_trace_data)

        failed_steps = trace.get_failed_steps()

        assert len(failed_steps) == 2

    def test_trace_get_failed_steps_empty_trace(self, minimal_trace_data: dict) -> None:
        """Test get_failed_steps with no steps."""
        minimal_trace_data["steps"] = []
        trace = ModelExecutionTrace(**minimal_trace_data)

        failed_steps = trace.get_failed_steps()

        assert failed_steps == []


# ============================================================================
# Test: Get Successful Steps
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceGetSuccessfulSteps:
    """Test get_successful_steps method."""

    def test_trace_get_successful_steps(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test retrieving only successful steps."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_failed]
        trace = ModelExecutionTrace(**minimal_trace_data)

        successful_steps = trace.get_successful_steps()

        assert len(successful_steps) == 1
        assert successful_steps[0].name == "fetch_data"


# ============================================================================
# Test: Get Skipped Steps
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceGetSkippedSteps:
    """Test get_skipped_steps method."""

    def test_trace_get_skipped_steps(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_skipped: ModelExecutionTraceStep,
    ) -> None:
        """Test retrieving only skipped steps."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_skipped]
        trace = ModelExecutionTrace(**minimal_trace_data)

        skipped_steps = trace.get_skipped_steps()

        assert len(skipped_steps) == 1
        assert skipped_steps[0].name == "optional_validation"


# ============================================================================
# Test: Is Successful
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceIsSuccessful:
    """Test is_successful method."""

    def test_trace_is_successful_true_when_status_success(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
    ) -> None:
        """Test is_successful returns True when status=SUCCESS."""
        minimal_trace_data["status"] = EnumExecutionStatus.SUCCESS
        minimal_trace_data["steps"] = [sample_step_success]
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.is_successful() is True

    def test_trace_is_successful_true_when_status_completed(
        self, minimal_trace_data: dict
    ) -> None:
        """Test is_successful returns True when status=COMPLETED."""
        minimal_trace_data["status"] = EnumExecutionStatus.COMPLETED
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.is_successful() is True

    def test_trace_is_successful_false_when_status_failed(
        self,
        minimal_trace_data: dict,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test is_successful returns False when status=FAILED."""
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        minimal_trace_data["steps"] = [sample_step_failed]
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.is_successful() is False

    def test_trace_is_failure_true_when_status_failed(
        self, minimal_trace_data: dict
    ) -> None:
        """Test is_failure returns True when status=FAILED."""
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.is_failure() is True

    def test_trace_is_failure_true_when_status_timeout(
        self, minimal_trace_data: dict
    ) -> None:
        """Test is_failure returns True when status=TIMEOUT."""
        minimal_trace_data["status"] = EnumExecutionStatus.TIMEOUT
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.is_failure() is True


# ============================================================================
# Test: Correlation ID
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceCorrelationId:
    """Test correlation ID handling."""

    def test_trace_with_correlation_id(self, minimal_trace_data: dict) -> None:
        """Test trace creation with correlation_id."""
        correlation_id = uuid4()
        minimal_trace_data["correlation_id"] = correlation_id
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.correlation_id == correlation_id
        assert isinstance(trace.correlation_id, UUID)

    def test_trace_correlation_id_preserved_in_serialization(
        self, minimal_trace_data: dict
    ) -> None:
        """Test correlation_id is preserved through JSON serialization."""
        correlation_id = uuid4()
        minimal_trace_data["correlation_id"] = correlation_id
        trace = ModelExecutionTrace(**minimal_trace_data)

        json_str = trace.model_dump_json()
        restored = ModelExecutionTrace.model_validate_json(json_str)

        assert restored.correlation_id == correlation_id


# ============================================================================
# Test: Dispatch ID Optional
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceDispatchId:
    """Test dispatch ID handling."""

    def test_trace_dispatch_id_optional(self, minimal_trace_data: dict) -> None:
        """Test dispatch_id is optional and defaults to None."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.dispatch_id is None

    def test_trace_with_dispatch_id(self, minimal_trace_data: dict) -> None:
        """Test trace creation with dispatch_id."""
        dispatch_id = uuid4()
        minimal_trace_data["dispatch_id"] = dispatch_id
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert trace.dispatch_id == dispatch_id
        assert isinstance(trace.dispatch_id, UUID)

    def test_trace_dispatch_id_preserved_in_serialization(
        self, minimal_trace_data: dict
    ) -> None:
        """Test dispatch_id is preserved through JSON serialization."""
        dispatch_id = uuid4()
        minimal_trace_data["dispatch_id"] = dispatch_id
        trace = ModelExecutionTrace(**minimal_trace_data)

        json_str = trace.model_dump_json()
        restored = ModelExecutionTrace.model_validate_json(json_str)

        assert restored.dispatch_id == dispatch_id

    def test_trace_has_dispatch(self, minimal_trace_data: dict) -> None:
        """Test has_dispatch() returns True when dispatch_id is set."""
        minimal_trace_data["dispatch_id"] = uuid4()
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_dispatch() is True

    def test_trace_has_dispatch_false(self, minimal_trace_data: dict) -> None:
        """Test has_dispatch() returns False when dispatch_id is None."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_dispatch() is False


# ============================================================================
# Test: Status Enum Values
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStatusEnumValues:
    """Test status enum values."""

    def test_status_enum_values(self) -> None:
        """Test all expected EnumExecutionStatus values exist."""
        assert hasattr(EnumExecutionStatus, "PENDING")
        assert hasattr(EnumExecutionStatus, "RUNNING")
        assert hasattr(EnumExecutionStatus, "COMPLETED")
        assert hasattr(EnumExecutionStatus, "SUCCESS")
        assert hasattr(EnumExecutionStatus, "FAILED")
        assert hasattr(EnumExecutionStatus, "SKIPPED")
        assert hasattr(EnumExecutionStatus, "CANCELLED")
        assert hasattr(EnumExecutionStatus, "TIMEOUT")
        assert hasattr(EnumExecutionStatus, "PARTIAL")

    def test_status_pending(self, minimal_trace_data: dict) -> None:
        """Test trace with PENDING status."""
        minimal_trace_data["status"] = EnumExecutionStatus.PENDING
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.PENDING

    def test_status_running(self, minimal_trace_data: dict) -> None:
        """Test trace with RUNNING status."""
        minimal_trace_data["status"] = EnumExecutionStatus.RUNNING
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.RUNNING
        assert trace.is_running() is True

    def test_status_completed(self, minimal_trace_data: dict) -> None:
        """Test trace with COMPLETED status."""
        minimal_trace_data["status"] = EnumExecutionStatus.COMPLETED
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.COMPLETED

    def test_status_failed(self, minimal_trace_data: dict) -> None:
        """Test trace with FAILED status."""
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.FAILED

    def test_status_skipped(self, minimal_trace_data: dict) -> None:
        """Test trace with SKIPPED status."""
        minimal_trace_data["status"] = EnumExecutionStatus.SKIPPED
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.SKIPPED

    def test_status_cancelled(self, minimal_trace_data: dict) -> None:
        """Test trace with CANCELLED status."""
        minimal_trace_data["status"] = EnumExecutionStatus.CANCELLED
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.CANCELLED
        assert trace.is_cancelled() is True

    def test_status_timeout(self, minimal_trace_data: dict) -> None:
        """Test trace with TIMEOUT status."""
        minimal_trace_data["status"] = EnumExecutionStatus.TIMEOUT
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.TIMEOUT

    def test_status_partial(self, minimal_trace_data: dict) -> None:
        """Test trace with PARTIAL status."""
        minimal_trace_data["status"] = EnumExecutionStatus.PARTIAL
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.status == EnumExecutionStatus.PARTIAL
        assert trace.is_partial() is True


# ============================================================================
# Test: Time Ordering Validation (ended_at >= started_at)
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceTimeOrdering:
    """Test time ordering validation (ended_at must be >= started_at)."""

    def test_valid_time_ordering_same_time(self, minimal_trace_data: dict) -> None:
        """Test that same start and end time is valid (instant execution)."""
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_trace_data["started_at"] = now
        minimal_trace_data["ended_at"] = now
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.started_at == trace.ended_at

    def test_valid_time_ordering_different_times(
        self, minimal_trace_data: dict
    ) -> None:
        """Test that ended_at > started_at is valid (normal case)."""
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        minimal_trace_data["started_at"] = start
        minimal_trace_data["ended_at"] = end
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.ended_at > trace.started_at

    def test_invalid_time_ordering_raises(self, minimal_trace_data: dict) -> None:
        """Test that ended_at < started_at raises ValidationError."""
        start = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)  # Before start
        minimal_trace_data["started_at"] = start
        minimal_trace_data["ended_at"] = end
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(**minimal_trace_data)
        error_str = str(exc_info.value)
        assert "ended_at" in error_str
        assert "started_at" in error_str
        assert "cannot be before" in error_str


# ============================================================================
# Test: Utility Methods
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceUtilityMethods:
    """Test utility methods on ModelExecutionTrace."""

    def test_get_step_count(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_step_count returns correct count."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.get_step_count() == 2

    def test_get_step_count_empty(self, minimal_trace_data: dict) -> None:
        """Test get_step_count returns 0 for empty steps."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.get_step_count() == 0

    def test_has_steps(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
    ) -> None:
        """Test has_steps returns True when steps exist."""
        minimal_trace_data["steps"] = [sample_step_success]
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_steps() is True

    def test_has_steps_false(self, minimal_trace_data: dict) -> None:
        """Test has_steps returns False when no steps."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_steps() is False

    def test_has_failures(
        self,
        minimal_trace_data: dict,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test has_failures returns True when failed steps exist."""
        minimal_trace_data["steps"] = [sample_step_failed]
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_failures() is True

    def test_has_failures_false(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
    ) -> None:
        """Test has_failures returns False when no failed steps."""
        minimal_trace_data["steps"] = [sample_step_success]
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.has_failures() is False

    def test_get_failure_count(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_failed: ModelExecutionTraceStep,
    ) -> None:
        """Test get_failure_count returns correct count."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_failed]
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.get_failure_count() == 1

    def test_get_step_by_id(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_step_by_id returns correct step."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        step = trace.get_step_by_id("step-002")
        assert step is not None
        assert step.name == "transform_data"

    def test_get_step_by_id_not_found(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
    ) -> None:
        """Test get_step_by_id returns None when not found."""
        minimal_trace_data["steps"] = [sample_step_success]
        trace = ModelExecutionTrace(**minimal_trace_data)

        step = trace.get_step_by_id("nonexistent")
        assert step is None

    def test_get_steps_by_kind(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_steps_by_kind returns correct steps."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        handler_steps = trace.get_steps_by_kind("handler")
        assert len(handler_steps) == 1
        assert handler_steps[0].name == "fetch_data"

        effect_steps = trace.get_steps_by_kind("effect_call")
        assert len(effect_steps) == 1
        assert effect_steps[0].name == "transform_data"

    def test_get_total_step_duration_ms(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_total_step_duration_ms sums all step durations."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        total = trace.get_total_step_duration_ms()
        # 2000 + 3000 = 5000
        assert total == 5000.0

    def test_get_slowest_step(
        self,
        minimal_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test get_slowest_step returns step with longest duration."""
        minimal_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**minimal_trace_data)

        slowest = trace.get_slowest_step()
        assert slowest is not None
        # sample_step_effect has 3000ms, sample_step_success has 2000ms
        assert slowest.name == "transform_data"
        assert slowest.duration_ms == 3000.0

    def test_get_slowest_step_empty(self, minimal_trace_data: dict) -> None:
        """Test get_slowest_step returns None when no steps."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.get_slowest_step() is None

    def test_is_terminal(self, minimal_trace_data: dict) -> None:
        """Test is_terminal returns True for terminal statuses."""
        minimal_trace_data["status"] = EnumExecutionStatus.SUCCESS
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.is_terminal() is True

        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.is_terminal() is True

    def test_is_terminal_false_for_running(self, minimal_trace_data: dict) -> None:
        """Test is_terminal returns False for RUNNING status."""
        minimal_trace_data["status"] = EnumExecutionStatus.RUNNING
        trace = ModelExecutionTrace(**minimal_trace_data)
        assert trace.is_terminal() is False


# ============================================================================
# Test: JSON Serialization Roundtrip
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceSerialization:
    """Test JSON serialization and deserialization."""

    def test_trace_json_serialization_roundtrip(
        self,
        full_trace_data: dict,
        sample_step_success: ModelExecutionTraceStep,
        sample_step_effect: ModelExecutionTraceStep,
    ) -> None:
        """Test full JSON serialization and deserialization roundtrip."""
        full_trace_data["steps"] = [sample_step_success, sample_step_effect]
        trace = ModelExecutionTrace(**full_trace_data)

        # Serialize to JSON
        json_str = trace.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        restored = ModelExecutionTrace.model_validate_json(json_str)

        # Verify all fields match
        assert restored.trace_id == trace.trace_id
        assert restored.correlation_id == trace.correlation_id
        assert restored.dispatch_id == trace.dispatch_id
        assert restored.run_id == trace.run_id
        assert restored.started_at == trace.started_at
        assert restored.ended_at == trace.ended_at
        assert restored.status == trace.status
        assert len(restored.steps) == len(trace.steps)

    def test_trace_json_serialization_minimal(self, minimal_trace_data: dict) -> None:
        """Test JSON roundtrip with minimal data."""
        trace = ModelExecutionTrace(**minimal_trace_data)

        json_str = trace.model_dump_json()
        restored = ModelExecutionTrace.model_validate_json(json_str)

        assert restored.trace_id == trace.trace_id
        assert restored.status == trace.status

    def test_trace_model_dump_contains_all_fields(self, full_trace_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        trace = ModelExecutionTrace(**full_trace_data)
        data = trace.model_dump()

        assert "trace_id" in data
        assert "correlation_id" in data
        assert "dispatch_id" in data
        assert "run_id" in data
        assert "started_at" in data
        assert "ended_at" in data
        assert "status" in data
        assert "steps" in data

    def test_trace_model_validate_from_dict(self, full_trace_data: dict) -> None:
        """Test model validation from dictionary."""
        trace = ModelExecutionTrace.model_validate(full_trace_data)
        assert trace.trace_id == full_trace_data["trace_id"]
        assert trace.status == full_trace_data["status"]


# ============================================================================
# Test: Edge Cases and Error Conditions
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceEdgeCases:
    """Test edge cases for ModelExecutionTrace."""

    def test_correlation_id_required(self) -> None:
        """Test that correlation_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(
                run_id=uuid4(),
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                status=EnumExecutionStatus.SUCCESS,
            )
        assert "correlation_id" in str(exc_info.value)

    def test_run_id_required(self) -> None:
        """Test that run_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(
                correlation_id=uuid4(),
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                status=EnumExecutionStatus.SUCCESS,
            )
        assert "run_id" in str(exc_info.value)

    def test_started_at_required(self) -> None:
        """Test that started_at is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(
                correlation_id=uuid4(),
                run_id=uuid4(),
                ended_at=datetime.now(UTC),
                status=EnumExecutionStatus.SUCCESS,
            )
        assert "started_at" in str(exc_info.value)

    def test_ended_at_required(self) -> None:
        """Test that ended_at is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(
                correlation_id=uuid4(),
                run_id=uuid4(),
                started_at=datetime.now(UTC),
                status=EnumExecutionStatus.SUCCESS,
            )
        assert "ended_at" in str(exc_info.value)

    def test_status_required(self) -> None:
        """Test that status is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(
                correlation_id=uuid4(),
                run_id=uuid4(),
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )
        assert "status" in str(exc_info.value)

    def test_invalid_status_raises_validation_error(
        self, minimal_trace_data: dict
    ) -> None:
        """Test that invalid status raises ValidationError."""
        minimal_trace_data["status"] = "invalid_status"
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(**minimal_trace_data)
        assert "status" in str(exc_info.value)

    def test_trace_with_large_number_of_steps(self, minimal_trace_data: dict) -> None:
        """Test trace with many steps."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        steps = [
            ModelExecutionTraceStep(
                step_id=f"step-{i:03d}",
                step_kind="handler",
                name=f"step_{i}",
                # Use microseconds offset to avoid invalid seconds
                start_ts=datetime(2025, 1, 1, 12 + (i // 60), i % 60, 0, tzinfo=UTC),
                end_ts=datetime(
                    2025, 1, 1, 12 + ((i + 1) // 60), (i + 1) % 60, 0, tzinfo=UTC
                ),
                duration_ms=1000.0,
                status="success",
            )
            for i in range(100)
        ]
        minimal_trace_data["steps"] = steps
        trace = ModelExecutionTrace(**minimal_trace_data)

        assert len(trace.steps) == 100
        assert trace.steps[50].name == "step_50"
        assert trace.get_step_count() == 100

    def test_trace_model_equality(self, minimal_trace_data: dict) -> None:
        """Test model equality comparison."""
        # Set explicit trace_id since default_factory creates unique UUIDs
        trace_id = uuid4()
        minimal_trace_data["trace_id"] = trace_id
        trace1 = ModelExecutionTrace(**minimal_trace_data)
        trace2 = ModelExecutionTrace(**minimal_trace_data)
        # Same data with same trace_id should produce equal models
        assert trace1 == trace2

    def test_trace_model_inequality(self, minimal_trace_data: dict) -> None:
        """Test model inequality when fields differ."""
        trace1 = ModelExecutionTrace(**minimal_trace_data)
        minimal_trace_data["status"] = EnumExecutionStatus.FAILED
        trace2 = ModelExecutionTrace(**minimal_trace_data)
        assert trace1 != trace2

    def test_frozen_model_immutability(self, minimal_trace_data: dict) -> None:
        """Test that the model is frozen (immutable)."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        with pytest.raises(ValidationError):
            trace.status = EnumExecutionStatus.FAILED  # type: ignore[misc]

    def test_extra_fields_forbidden(self, minimal_trace_data: dict) -> None:
        """Test that extra fields are rejected."""
        minimal_trace_data["extra_field"] = "should_fail"
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTrace(**minimal_trace_data)
        assert "extra" in str(exc_info.value).lower()

    def test_str_representation(self, minimal_trace_data: dict) -> None:
        """Test __str__ method."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        str_repr = str(trace)
        assert "ExecutionTrace" in str_repr
        assert "success" in str_repr.lower()

    def test_repr_representation(self, minimal_trace_data: dict) -> None:
        """Test __repr__ method."""
        trace = ModelExecutionTrace(**minimal_trace_data)
        repr_str = repr(trace)
        assert "ModelExecutionTrace" in repr_str
        assert "trace_id" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
