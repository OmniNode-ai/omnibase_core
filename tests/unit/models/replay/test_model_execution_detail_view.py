"""Tests for execution detail view models.

Covers the 8 models used for detailed drill-down views of execution comparisons:
- ModelDiffLine: Single line in diff output
- ModelPhaseTime: Timing for a specific execution phase
- ModelInputSnapshot: Snapshot of execution input
- ModelOutputSnapshot: Snapshot of execution output
- ModelInvariantResultDetail: Detailed invariant result for display
- ModelTimingBreakdown: Detailed timing breakdown
- ModelSideBySideComparison: Side-by-side formatted comparison
- ModelExecutionDetailView: Complete execution detail view
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import (
    ModelDiffLine,
    ModelExecutionDetailView,
    ModelInputSnapshot,
    ModelInvariantResultDetail,
    ModelOutputSnapshot,
    ModelPhaseTime,
    ModelSideBySideComparison,
    ModelTimingBreakdown,
)

# Test UUIDs for deterministic testing
TEST_COMPARISON_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_BASELINE_ID = UUID("22345678-1234-5678-1234-567812345678")
TEST_REPLAY_ID = UUID("32345678-1234-5678-1234-567812345678")
TEST_CORPUS_ID = UUID("42345678-1234-5678-1234-567812345678")


@pytest.mark.unit
class TestModelDiffLine:
    """Tests for ModelDiffLine."""

    def test_create_unchanged_line(self) -> None:
        """Create a diff line with unchanged status."""
        diff_line = ModelDiffLine(
            line_number=1,
            baseline_content="same content",
            replay_content="same content",
            change_type="unchanged",
        )
        assert diff_line.line_number == 1
        assert diff_line.baseline_content == "same content"
        assert diff_line.replay_content == "same content"
        assert diff_line.change_type == "unchanged"

    def test_create_modified_line(self) -> None:
        """Create a diff line with modified status."""
        diff_line = ModelDiffLine(
            line_number=5,
            baseline_content="original text",
            replay_content="modified text",
            change_type="modified",
        )
        assert diff_line.line_number == 5
        assert diff_line.baseline_content == "original text"
        assert diff_line.replay_content == "modified text"
        assert diff_line.change_type == "modified"

    def test_create_added_line(self) -> None:
        """Create a diff line with added status (baseline_content is None)."""
        diff_line = ModelDiffLine(
            line_number=10,
            baseline_content=None,
            replay_content="new line added",
            change_type="added",
        )
        assert diff_line.line_number == 10
        assert diff_line.baseline_content is None
        assert diff_line.replay_content == "new line added"
        assert diff_line.change_type == "added"

    def test_create_removed_line(self) -> None:
        """Create a diff line with removed status (replay_content is None)."""
        diff_line = ModelDiffLine(
            line_number=15,
            baseline_content="line to be removed",
            replay_content=None,
            change_type="removed",
        )
        assert diff_line.line_number == 15
        assert diff_line.baseline_content == "line to be removed"
        assert diff_line.replay_content is None
        assert diff_line.change_type == "removed"

    def test_invalid_change_type_rejected(self) -> None:
        """Invalid change_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="content",
                replay_content="content",
                change_type="invalid_type",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("change_type",)

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        diff_line = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        with pytest.raises(ValidationError):
            diff_line.line_number = 2
        with pytest.raises(ValidationError):
            diff_line.change_type = "modified"


@pytest.mark.unit
class TestModelPhaseTime:
    """Tests for ModelPhaseTime."""

    def test_create_phase_time(self) -> None:
        """Create a phase time entry."""
        phase_time = ModelPhaseTime(
            phase_name="initialization",
            baseline_ms=100.5,
            replay_ms=95.2,
            delta_percent=-5.27,
        )
        assert phase_time.phase_name == "initialization"
        assert phase_time.baseline_ms == 100.5
        assert phase_time.replay_ms == 95.2
        assert phase_time.delta_percent == -5.27

    def test_negative_times_allowed(self) -> None:
        """Negative delta_percent is valid (replay faster than baseline)."""
        # Replay is faster: 100ms baseline, 50ms replay = -50% delta
        phase_time = ModelPhaseTime(
            phase_name="computation",
            baseline_ms=100.0,
            replay_ms=50.0,
            delta_percent=-50.0,
        )
        assert phase_time.delta_percent == -50.0

    def test_positive_delta_percent(self) -> None:
        """Positive delta_percent is valid (replay slower than baseline)."""
        # Replay is slower: 100ms baseline, 150ms replay = +50% delta
        phase_time = ModelPhaseTime(
            phase_name="rendering",
            baseline_ms=100.0,
            replay_ms=150.0,
            delta_percent=50.0,
        )
        assert phase_time.delta_percent == 50.0

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        phase_time = ModelPhaseTime(
            phase_name="test_phase",
            baseline_ms=100.0,
            replay_ms=100.0,
            delta_percent=0.0,
        )
        with pytest.raises(ValidationError):
            phase_time.phase_name = "modified_phase"
        with pytest.raises(ValidationError):
            phase_time.baseline_ms = 200.0


@pytest.mark.unit
class TestModelInputSnapshot:
    """Tests for ModelInputSnapshot."""

    def test_create_non_truncated_snapshot(self) -> None:
        """Create a non-truncated input snapshot."""
        raw_data: dict[str, Any] = {"key": "value", "nested": {"data": 123}}
        snapshot = ModelInputSnapshot(
            raw=raw_data,
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.raw == raw_data
        assert snapshot.truncated is False
        assert snapshot.original_size_bytes == 100
        assert snapshot.display_size_bytes == 100

    def test_create_truncated_snapshot(self) -> None:
        """Create a truncated input snapshot with size metadata."""
        truncated_data: dict[str, Any] = {"partial": "data..."}
        snapshot = ModelInputSnapshot(
            raw=truncated_data,
            truncated=True,
            original_size_bytes=50000,
            display_size_bytes=1000,
        )
        assert snapshot.truncated is True
        assert snapshot.original_size_bytes == 50000
        assert snapshot.display_size_bytes == 1000
        assert snapshot.original_size_bytes > snapshot.display_size_bytes

    def test_default_truncated_false(self) -> None:
        """Default value for truncated is False."""
        snapshot = ModelInputSnapshot(
            raw={"test": "data"},
            original_size_bytes=50,
            display_size_bytes=50,
        )
        assert snapshot.truncated is False

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
        )
        with pytest.raises(ValidationError):
            snapshot.truncated = True
        with pytest.raises(ValidationError):
            snapshot.original_size_bytes = 100


@pytest.mark.unit
class TestModelOutputSnapshot:
    """Tests for ModelOutputSnapshot."""

    def test_create_output_snapshot(self) -> None:
        """Create an output snapshot with hash."""
        raw_data: dict[str, Any] = {"result": "success", "data": [1, 2, 3]}
        snapshot = ModelOutputSnapshot(
            raw=raw_data,
            truncated=False,
            original_size_bytes=200,
            display_size_bytes=200,
            output_hash="sha256:abc123def456",
        )
        assert snapshot.raw == raw_data
        assert snapshot.truncated is False
        assert snapshot.original_size_bytes == 200
        assert snapshot.display_size_bytes == 200
        assert snapshot.output_hash == "sha256:abc123def456"

    def test_truncated_preserves_hash(self) -> None:
        """Truncated snapshot still has output_hash."""
        # Even when truncated, the hash represents the full original output
        snapshot = ModelOutputSnapshot(
            raw={"truncated": "data"},
            truncated=True,
            original_size_bytes=100000,
            display_size_bytes=1000,
            output_hash="sha256:abcdef123456789012345678901234567890abcdef",
        )
        assert snapshot.truncated is True
        assert (
            snapshot.output_hash == "sha256:abcdef123456789012345678901234567890abcdef"
        )

    def test_default_truncated_false(self) -> None:
        """Default value for truncated is False."""
        snapshot = ModelOutputSnapshot(
            raw={"output": "data"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:abc123",
        )
        assert snapshot.truncated is False

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
            output_hash="sha256:def456",
        )
        with pytest.raises(ValidationError):
            snapshot.output_hash = "sha256:fedcba987654"
        with pytest.raises(ValidationError):
            snapshot.truncated = True


@pytest.mark.unit
class TestModelInvariantResultDetail:
    """Tests for ModelInvariantResultDetail."""

    def test_unchanged_pass_status(self) -> None:
        """Both passed -> unchanged_pass."""
        result = ModelInvariantResultDetail(
            invariant_name="output_schema_valid",
            invariant_type="schema",
            baseline_passed=True,
            replay_passed=True,
            status_change="unchanged_pass",
        )
        assert result.baseline_passed is True
        assert result.replay_passed is True
        assert result.status_change == "unchanged_pass"

    def test_unchanged_fail_status(self) -> None:
        """Both failed -> unchanged_fail."""
        result = ModelInvariantResultDetail(
            invariant_name="latency_under_100ms",
            invariant_type="performance",
            baseline_passed=False,
            replay_passed=False,
            status_change="unchanged_fail",
            violation_message="Latency exceeded threshold in both executions",
        )
        assert result.baseline_passed is False
        assert result.replay_passed is False
        assert result.status_change == "unchanged_fail"
        assert result.violation_message is not None
        assert "Latency exceeded" in result.violation_message

    def test_regression_status(self) -> None:
        """Baseline passed, replay failed -> regression."""
        result = ModelInvariantResultDetail(
            invariant_name="response_not_empty",
            invariant_type="content",
            baseline_passed=True,
            replay_passed=False,
            status_change="regression",
            violation_message="Response was empty in replay",
        )
        assert result.baseline_passed is True
        assert result.replay_passed is False
        assert result.status_change == "regression"

    def test_improvement_status(self) -> None:
        """Baseline failed, replay passed -> improvement."""
        result = ModelInvariantResultDetail(
            invariant_name="error_count_zero",
            invariant_type="reliability",
            baseline_passed=False,
            replay_passed=True,
            status_change="improvement",
        )
        assert result.baseline_passed is False
        assert result.replay_passed is True
        assert result.status_change == "improvement"

    def test_violation_message_included(self) -> None:
        """Violation message included when failed."""
        result = ModelInvariantResultDetail(
            invariant_name="field_required",
            invariant_type="schema",
            baseline_passed=True,
            replay_passed=False,
            status_change="regression",
            violation_message="Required field 'user_id' is missing",
        )
        assert result.violation_message == "Required field 'user_id' is missing"

    def test_violation_details_optional(self) -> None:
        """Violation details can be None."""
        result = ModelInvariantResultDetail(
            invariant_name="basic_check",
            invariant_type="basic",
            baseline_passed=True,
            replay_passed=True,
            status_change="unchanged_pass",
        )
        assert result.violation_message is None
        assert result.violation_details is None

    def test_violation_details_with_data(self) -> None:
        """Violation details can contain structured data."""
        details: dict[str, Any] = {
            "expected": 100,
            "actual": 150,
            "field_path": "response.latency_ms",
        }
        result = ModelInvariantResultDetail(
            invariant_name="latency_check",
            invariant_type="performance",
            baseline_passed=True,
            replay_passed=False,
            status_change="regression",
            violation_message="Latency threshold exceeded",
            violation_details=details,
        )
        assert result.violation_details == details
        assert result.violation_details["expected"] == 100

    def test_invalid_status_change_rejected(self) -> None:
        """Invalid status_change raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantResultDetail(
                invariant_name="test",
                invariant_type="test",
                baseline_passed=True,
                replay_passed=True,
                status_change="invalid_status",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("status_change",)

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        result = ModelInvariantResultDetail(
            invariant_name="test_invariant",
            invariant_type="test",
            baseline_passed=True,
            replay_passed=True,
            status_change="unchanged_pass",
        )
        with pytest.raises(ValidationError):
            result.status_change = "regression"
        with pytest.raises(ValidationError):
            result.baseline_passed = False


@pytest.mark.unit
class TestModelTimingBreakdown:
    """Tests for ModelTimingBreakdown."""

    def test_create_timing_breakdown(self) -> None:
        """Create timing breakdown with required fields."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=250.0,
            replay_total_ms=275.0,
            delta_ms=25.0,
            delta_percent=10.0,
        )
        assert breakdown.baseline_total_ms == 250.0
        assert breakdown.replay_total_ms == 275.0
        assert breakdown.delta_ms == 25.0
        assert breakdown.delta_percent == 10.0

    def test_phases_optional(self) -> None:
        """Phases can be None."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        assert breakdown.phases is None

    def test_phases_with_data(self) -> None:
        """Phases can contain ModelPhaseTime list."""
        phases = [
            ModelPhaseTime(
                phase_name="init",
                baseline_ms=50.0,
                replay_ms=45.0,
                delta_percent=-10.0,
            ),
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=150.0,
                replay_ms=180.0,
                delta_percent=20.0,
            ),
        ]
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=200.0,
            replay_total_ms=225.0,
            delta_ms=25.0,
            delta_percent=12.5,
            phases=phases,
        )
        assert breakdown.phases is not None
        assert len(breakdown.phases) == 2
        assert breakdown.phases[0].phase_name == "init"
        assert breakdown.phases[1].phase_name == "compute"

    def test_negative_delta_valid(self) -> None:
        """Negative delta (replay faster) is valid."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=200.0,
            replay_total_ms=150.0,
            delta_ms=-50.0,
            delta_percent=-25.0,
        )
        assert breakdown.delta_ms == -50.0
        assert breakdown.delta_percent == -25.0

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        with pytest.raises(ValidationError):
            breakdown.baseline_total_ms = 200.0
        with pytest.raises(ValidationError):
            breakdown.phases = []

    def test_negative_baseline_total_ms_rejected(self) -> None:
        """Negative baseline_total_ms raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=-100.0,  # Invalid: must be >= 0
                replay_total_ms=150.0,
                delta_ms=250.0,
                delta_percent=250.0,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("baseline_total_ms",)
        assert errors[0]["type"] == "greater_than_equal"

    def test_negative_replay_total_ms_rejected(self) -> None:
        """Negative replay_total_ms raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=-50.0,  # Invalid: must be >= 0
                delta_ms=-150.0,
                delta_percent=-150.0,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("replay_total_ms",)
        assert errors[0]["type"] == "greater_than_equal"

    def test_both_negative_timings_rejected(self) -> None:
        """Both negative timing values raise ValidationError with multiple errors."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=-100.0,  # Invalid
                replay_total_ms=-50.0,  # Invalid
                delta_ms=50.0,
                delta_percent=50.0,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 2
        error_locs = {e["loc"] for e in errors}
        assert ("baseline_total_ms",) in error_locs
        assert ("replay_total_ms",) in error_locs

    def test_zero_timing_values_valid(self) -> None:
        """Zero timing values are valid (edge case for boundary)."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=0.0,
            replay_total_ms=0.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        assert breakdown.baseline_total_ms == 0.0
        assert breakdown.replay_total_ms == 0.0


@pytest.mark.unit
class TestModelSideBySideComparison:
    """Tests for ModelSideBySideComparison."""

    def test_create_comparison(self) -> None:
        """Create a side-by-side comparison."""
        diff_lines = [
            ModelDiffLine(
                line_number=1,
                baseline_content='{"key": "old"}',
                replay_content='{"key": "new"}',
                change_type="modified",
            ),
        ]
        comparison = ModelSideBySideComparison(
            baseline_formatted='{\n  "key": "old"\n}',
            replay_formatted='{\n  "key": "new"\n}',
            diff_lines=diff_lines,
        )
        assert comparison.baseline_formatted == '{\n  "key": "old"\n}'
        assert comparison.replay_formatted == '{\n  "key": "new"\n}'
        assert len(comparison.diff_lines) == 1

    def test_empty_diff_lines_valid(self) -> None:
        """Empty diff_lines list is valid (identical outputs)."""
        comparison = ModelSideBySideComparison(
            baseline_formatted='{"same": "content"}',
            replay_formatted='{"same": "content"}',
            diff_lines=[],
        )
        assert len(comparison.diff_lines) == 0

    def test_diff_lines_with_changes(self) -> None:
        """Diff lines capture various change types."""
        diff_lines = [
            ModelDiffLine(
                line_number=1,
                baseline_content="{",
                replay_content="{",
                change_type="unchanged",
            ),
            ModelDiffLine(
                line_number=2,
                baseline_content='  "old_key": 1',
                replay_content=None,
                change_type="removed",
            ),
            ModelDiffLine(
                line_number=3,
                baseline_content=None,
                replay_content='  "new_key": 2',
                change_type="added",
            ),
            ModelDiffLine(
                line_number=4,
                baseline_content='  "value": 100',
                replay_content='  "value": 200',
                change_type="modified",
            ),
            ModelDiffLine(
                line_number=5,
                baseline_content="}",
                replay_content="}",
                change_type="unchanged",
            ),
        ]
        comparison = ModelSideBySideComparison(
            baseline_formatted="baseline json",
            replay_formatted="replay json",
            diff_lines=diff_lines,
        )
        assert len(comparison.diff_lines) == 5
        change_types = [line.change_type for line in comparison.diff_lines]
        assert "unchanged" in change_types
        assert "removed" in change_types
        assert "added" in change_types
        assert "modified" in change_types

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        comparison = ModelSideBySideComparison(
            baseline_formatted="baseline",
            replay_formatted="replay",
            diff_lines=[],
        )
        with pytest.raises(ValidationError):
            comparison.baseline_formatted = "modified"
        with pytest.raises(ValidationError):
            comparison.diff_lines = []


@pytest.mark.unit
class TestModelExecutionDetailView:
    """Tests for ModelExecutionDetailView."""

    @pytest.fixture
    def sample_input_snapshot(self) -> ModelInputSnapshot:
        """Provide sample input snapshot for tests."""
        return ModelInputSnapshot(
            raw={"prompt": "Hello, world!"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )

    @pytest.fixture
    def sample_baseline_output(self) -> ModelOutputSnapshot:
        """Provide sample baseline output snapshot."""
        return ModelOutputSnapshot(
            raw={"response": "Hello from baseline!"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:abc123def456789012345678901234567890abcdef",
        )

    @pytest.fixture
    def sample_replay_output(self) -> ModelOutputSnapshot:
        """Provide sample replay output snapshot."""
        return ModelOutputSnapshot(
            raw={"response": "Hello from replay!"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:def456789012345678901234567890abcdef123456",
        )

    @pytest.fixture
    def sample_matching_replay_output(self) -> ModelOutputSnapshot:
        """Provide replay output that matches baseline."""
        return ModelOutputSnapshot(
            raw={"response": "Hello from baseline!"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:abc123def456789012345678901234567890abcdef",  # Same hash as baseline
        )

    @pytest.fixture
    def sample_side_by_side(self) -> ModelSideBySideComparison:
        """Provide sample side-by-side comparison."""
        return ModelSideBySideComparison(
            baseline_formatted='{\n  "response": "Hello from baseline!"\n}',
            replay_formatted='{\n  "response": "Hello from replay!"\n}',
            diff_lines=[
                ModelDiffLine(
                    line_number=2,
                    baseline_content='  "response": "Hello from baseline!"',
                    replay_content='  "response": "Hello from replay!"',
                    change_type="modified",
                ),
            ],
        )

    @pytest.fixture
    def sample_timing_breakdown(self) -> ModelTimingBreakdown:
        """Provide sample timing breakdown."""
        return ModelTimingBreakdown(
            baseline_total_ms=200.0,
            replay_total_ms=220.0,
            delta_ms=20.0,
            delta_percent=10.0,
        )

    @pytest.fixture
    def sample_invariant_results(self) -> list[ModelInvariantResultDetail]:
        """Provide sample invariant results."""
        return [
            ModelInvariantResultDetail(
                invariant_name="schema_valid",
                invariant_type="schema",
                baseline_passed=True,
                replay_passed=True,
                status_change="unchanged_pass",
            ),
            ModelInvariantResultDetail(
                invariant_name="latency_check",
                invariant_type="performance",
                baseline_passed=True,
                replay_passed=True,
                status_change="unchanged_pass",
            ),
        ]

    def test_create_full_detail_view(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_replay_output: ModelOutputSnapshot,
        sample_side_by_side: ModelSideBySideComparison,
        sample_timing_breakdown: ModelTimingBreakdown,
        sample_invariant_results: list[ModelInvariantResultDetail],
    ) -> None:
        """Create a complete execution detail view."""
        detail_view = ModelExecutionDetailView(
            comparison_id=TEST_COMPARISON_ID,
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            original_input=sample_input_snapshot,
            input_hash="sha256:abc123def456",
            input_display='{"prompt": "Hello, world!"}',
            baseline_output=sample_baseline_output,
            replay_output=sample_replay_output,
            output_diff_display="- baseline response\n+ replay response",
            outputs_match=False,
            side_by_side=sample_side_by_side,
            invariant_results=sample_invariant_results,
            invariants_all_passed=True,
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=TEST_CORPUS_ID,
        )
        assert detail_view.comparison_id == TEST_COMPARISON_ID
        assert detail_view.baseline_execution_id == TEST_BASELINE_ID
        assert detail_view.replay_execution_id == TEST_REPLAY_ID
        assert detail_view.original_input == sample_input_snapshot
        assert detail_view.outputs_match is False
        assert len(detail_view.invariant_results) == 2
        assert detail_view.invariants_all_passed is True

    def test_outputs_match_true(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_matching_replay_output: ModelOutputSnapshot,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Detail view with matching outputs."""
        comparison_id = UUID("52345678-1234-5678-1234-567812345678")
        baseline_id = UUID("62345678-1234-5678-1234-567812345678")
        replay_id = UUID("72345678-1234-5678-1234-567812345678")
        corpus_id = UUID("82345678-1234-5678-1234-567812345678")
        side_by_side = ModelSideBySideComparison(
            baseline_formatted='{"response": "Hello from baseline!"}',
            replay_formatted='{"response": "Hello from baseline!"}',
            diff_lines=[],  # Empty because outputs match
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:def456abc123",
            input_display='{"prompt": "test"}',
            baseline_output=sample_baseline_output,
            replay_output=sample_matching_replay_output,
            output_diff_display=None,  # None when outputs match
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.outputs_match is True
        assert detail_view.output_diff_display is None
        assert len(detail_view.side_by_side.diff_lines) == 0

    def test_outputs_match_false_with_diff(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_replay_output: ModelOutputSnapshot,
        sample_side_by_side: ModelSideBySideComparison,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Detail view with diff when outputs don't match."""
        comparison_id = UUID("92345678-1234-5678-1234-567812345678")
        baseline_id = UUID("a2345678-1234-5678-1234-567812345678")
        replay_id = UUID("b2345678-1234-5678-1234-567812345678")
        corpus_id = UUID("c2345678-1234-5678-1234-567812345678")
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:fedcba654321",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_replay_output,
            output_diff_display="Differences:\n- old\n+ new",
            outputs_match=False,
            side_by_side=sample_side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.outputs_match is False
        assert detail_view.output_diff_display is not None
        assert "Differences" in detail_view.output_diff_display

    def test_all_invariants_passed(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Detail view where all invariants passed."""
        comparison_id = UUID("d2345678-1234-5678-1234-567812345678")
        baseline_id = UUID("e2345678-1234-5678-1234-567812345678")
        replay_id = UUID("f2345678-1234-5678-1234-567812345678")
        corpus_id = UUID("02345678-1234-5678-1234-567812345678")
        invariants = [
            ModelInvariantResultDetail(
                invariant_name="check_1",
                invariant_type="type_1",
                baseline_passed=True,
                replay_passed=True,
                status_change="unchanged_pass",
            ),
            ModelInvariantResultDetail(
                invariant_name="check_2",
                invariant_type="type_2",
                baseline_passed=True,
                replay_passed=True,
                status_change="unchanged_pass",
            ),
        ]
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:123abc456def",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_baseline_output,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=invariants,
            invariants_all_passed=True,
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.invariants_all_passed is True
        assert all(
            inv.status_change == "unchanged_pass"
            for inv in detail_view.invariant_results
        )

    def test_invariant_regression_detected(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Detail view with invariant regression."""
        comparison_id = UUID("12345679-1234-5678-1234-567812345678")
        baseline_id = UUID("22345679-1234-5678-1234-567812345678")
        replay_id = UUID("32345679-1234-5678-1234-567812345678")
        corpus_id = UUID("42345679-1234-5678-1234-567812345678")
        invariants = [
            ModelInvariantResultDetail(
                invariant_name="passing_check",
                invariant_type="type_1",
                baseline_passed=True,
                replay_passed=True,
                status_change="unchanged_pass",
            ),
            ModelInvariantResultDetail(
                invariant_name="regression_check",
                invariant_type="type_2",
                baseline_passed=True,
                replay_passed=False,
                status_change="regression",
                violation_message="Regression detected: response format changed",
            ),
        ]
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:123abc456def",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_baseline_output,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=invariants,
            invariants_all_passed=False,  # Has a regression
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.invariants_all_passed is False
        regression_invs = [
            inv
            for inv in detail_view.invariant_results
            if inv.status_change == "regression"
        ]
        assert len(regression_invs) == 1
        assert regression_invs[0].violation_message is not None
        assert "Regression detected" in regression_invs[0].violation_message

    def test_timing_with_phases(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
    ) -> None:
        """Detail view with phase-level timing."""
        comparison_id = UUID("52345679-1234-5678-1234-567812345678")
        baseline_id = UUID("62345679-1234-5678-1234-567812345678")
        replay_id = UUID("72345679-1234-5678-1234-567812345678")
        corpus_id = UUID("82345679-1234-5678-1234-567812345678")
        phases = [
            ModelPhaseTime(
                phase_name="initialization",
                baseline_ms=50.0,
                replay_ms=45.0,
                delta_percent=-10.0,
            ),
            ModelPhaseTime(
                phase_name="execution",
                baseline_ms=100.0,
                replay_ms=110.0,
                delta_percent=10.0,
            ),
            ModelPhaseTime(
                phase_name="cleanup",
                baseline_ms=25.0,
                replay_ms=20.0,
                delta_percent=-20.0,
            ),
        ]
        timing_breakdown = ModelTimingBreakdown(
            baseline_total_ms=175.0,
            replay_total_ms=175.0,
            delta_ms=0.0,
            delta_percent=0.0,
            phases=phases,
        )
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:123abc456def",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_baseline_output,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.timing_breakdown.phases is not None
        assert len(detail_view.timing_breakdown.phases) == 3
        phase_names = [p.phase_name for p in detail_view.timing_breakdown.phases]
        assert "initialization" in phase_names
        assert "execution" in phase_names
        assert "cleanup" in phase_names

    def test_timing_without_phases(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
    ) -> None:
        """Detail view without phase breakdown."""
        comparison_id = UUID("92345679-1234-5678-1234-567812345678")
        baseline_id = UUID("a2345679-1234-5678-1234-567812345678")
        replay_id = UUID("b2345679-1234-5678-1234-567812345678")
        corpus_id = UUID("c2345679-1234-5678-1234-567812345678")
        timing_breakdown = ModelTimingBreakdown(
            baseline_total_ms=200.0,
            replay_total_ms=210.0,
            delta_ms=10.0,
            delta_percent=5.0,
            phases=None,
        )
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:123abc456def",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_baseline_output,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        assert detail_view.timing_breakdown.phases is None
        assert detail_view.timing_breakdown.baseline_total_ms == 200.0
        assert detail_view.timing_breakdown.delta_percent == 5.0

    def test_frozen_immutable(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_side_by_side: ModelSideBySideComparison,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Model is immutable (frozen)."""
        comparison_id = UUID("d2345679-1234-5678-1234-567812345678")
        baseline_id = UUID("e2345679-1234-5678-1234-567812345678")
        replay_id = UUID("f2345679-1234-5678-1234-567812345678")
        corpus_id = UUID("02345679-1234-5678-1234-567812345678")
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=sample_input_snapshot,
            input_hash="sha256:123abc456def",
            input_display="{}",
            baseline_output=sample_baseline_output,
            replay_output=sample_baseline_output,
            outputs_match=True,
            side_by_side=sample_side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=sample_timing_breakdown,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )
        with pytest.raises(ValidationError):
            detail_view.comparison_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        with pytest.raises(ValidationError):
            detail_view.outputs_match = False
        with pytest.raises(ValidationError):
            detail_view.invariants_all_passed = False

    def test_from_attributes_works(
        self,
        sample_input_snapshot: ModelInputSnapshot,
        sample_baseline_output: ModelOutputSnapshot,
        sample_side_by_side: ModelSideBySideComparison,
        sample_timing_breakdown: ModelTimingBreakdown,
    ) -> None:
        """Model can be created from object with attributes."""
        attrs_comparison_id = UUID("1234567a-1234-5678-1234-567812345678")
        attrs_baseline_id = UUID("2234567a-1234-5678-1234-567812345678")
        attrs_replay_id = UUID("3234567a-1234-5678-1234-567812345678")
        attrs_corpus_id = UUID("4234567a-1234-5678-1234-567812345678")

        class DetailViewData:
            """Mock object with execution detail view attributes."""

            def __init__(self) -> None:
                self.comparison_id = attrs_comparison_id
                self.baseline_execution_id = attrs_baseline_id
                self.replay_execution_id = attrs_replay_id
                self.original_input = sample_input_snapshot
                self.input_hash = "sha256:aabbccdd1122"
                self.input_display = '{"from": "attributes"}'
                self.baseline_output = sample_baseline_output
                self.replay_output = sample_baseline_output
                self.output_diff_display = None
                self.outputs_match = True
                self.side_by_side = sample_side_by_side
                self.invariant_results: list[ModelInvariantResultDetail] = []
                self.invariants_all_passed = True
                self.timing_breakdown = sample_timing_breakdown
                self.execution_timestamp = datetime(2025, 1, 4, 15, 30, 0, tzinfo=UTC)
                self.corpus_entry_id = attrs_corpus_id

        data_obj = DetailViewData()
        detail_view = ModelExecutionDetailView.model_validate(data_obj)

        assert detail_view.comparison_id == attrs_comparison_id
        assert detail_view.baseline_execution_id == attrs_baseline_id
        assert detail_view.outputs_match is True
        assert detail_view.input_display == '{"from": "attributes"}'
        assert detail_view.corpus_entry_id == attrs_corpus_id


@pytest.mark.unit
class TestModelOutputSnapshotHashValidation:
    """Tests for output_hash validation in ModelOutputSnapshot."""

    def test_empty_output_hash_rejected(self) -> None:
        """Empty output_hash raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="",  # Empty string should be rejected
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_valid_sha256_hash(self) -> None:
        """Valid sha256 hash is accepted."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:abc123def456",
        )
        assert snapshot.output_hash == "sha256:abc123def456"

    def test_valid_md5_hash(self) -> None:
        """Valid md5 hash is accepted."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="md5:d41d8cd98f00b204e9800998ecf8427e",
        )
        assert snapshot.output_hash == "md5:d41d8cd98f00b204e9800998ecf8427e"

    def test_valid_sha1_hash(self) -> None:
        """Valid sha1 hash is accepted."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha1:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
        )
        assert snapshot.output_hash == "sha1:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"

    def test_valid_uppercase_algorithm_hash(self) -> None:
        """Uppercase algorithm name is accepted for flexibility."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="SHA256:abc123def456",
        )
        assert snapshot.output_hash == "SHA256:abc123def456"

    def test_valid_mixed_case_digest(self) -> None:
        """Mixed case hexadecimal digest is accepted."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:AbC123DeF456",
        )
        assert snapshot.output_hash == "sha256:AbC123DeF456"

    def test_invalid_hash_no_algorithm_prefix(self) -> None:
        """Hash without algorithm prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="abc123def456",  # Missing algorithm prefix
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)
        assert any("algorithm:hexdigest" in str(e["msg"]) for e in errors)

    def test_invalid_hash_empty_digest(self) -> None:
        """Hash with empty digest is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha256:",  # Empty digest
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_invalid_hash_empty_algorithm(self) -> None:
        """Hash with empty algorithm is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash=":abc123",  # Empty algorithm
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_invalid_hash_non_hex_digest(self) -> None:
        """Hash with non-hexadecimal digest is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha256:xyz123",  # 'xyz' is not valid hex
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_invalid_hash_special_chars_in_algorithm(self) -> None:
        """Hash with special characters in algorithm is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha-256:abc123",  # Hyphen not allowed
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_invalid_hash_multiple_colons(self) -> None:
        """Hash with multiple colons is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha256:abc:123",  # Multiple colons
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)


@pytest.mark.unit
class TestModelExecutionDetailViewInputHashValidation:
    """Tests for input_hash validation in ModelExecutionDetailView."""

    @pytest.fixture
    def input_snapshot(self) -> ModelInputSnapshot:
        """Provide input snapshot for hash validation tests."""
        return ModelInputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
        )

    @pytest.fixture
    def output_snapshot(self) -> ModelOutputSnapshot:
        """Provide output snapshot for hash validation tests."""
        return ModelOutputSnapshot(
            raw={"result": "data"},
            original_size_bytes=60,
            display_size_bytes=60,
            output_hash="sha256:abc123",
        )

    @pytest.fixture
    def side_by_side(self) -> ModelSideBySideComparison:
        """Provide side-by-side comparison for hash validation tests."""
        return ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )

    @pytest.fixture
    def timing(self) -> ModelTimingBreakdown:
        """Provide timing breakdown for hash validation tests."""
        return ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )

    def test_empty_input_hash_rejected(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Empty input_hash raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="",  # Empty string should be rejected
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)

    def test_valid_sha256_input_hash(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Valid sha256 input_hash is accepted."""
        detail_view = ModelExecutionDetailView(
            comparison_id=TEST_COMPARISON_ID,
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            original_input=input_snapshot,
            input_hash="sha256:abc123def456",
            input_display="{}",
            baseline_output=output_snapshot,
            replay_output=output_snapshot,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=TEST_CORPUS_ID,
        )
        assert detail_view.input_hash == "sha256:abc123def456"

    def test_valid_md5_input_hash(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Valid md5 input_hash is accepted."""
        detail_view = ModelExecutionDetailView(
            comparison_id=TEST_COMPARISON_ID,
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            original_input=input_snapshot,
            input_hash="md5:d41d8cd98f00b204e9800998ecf8427e",
            input_display="{}",
            baseline_output=output_snapshot,
            replay_output=output_snapshot,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=TEST_CORPUS_ID,
        )
        assert detail_view.input_hash == "md5:d41d8cd98f00b204e9800998ecf8427e"

    def test_valid_uppercase_algorithm_input_hash(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Uppercase algorithm name in input_hash is accepted for flexibility."""
        detail_view = ModelExecutionDetailView(
            comparison_id=TEST_COMPARISON_ID,
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            original_input=input_snapshot,
            input_hash="SHA256:abc123def456",
            input_display="{}",
            baseline_output=output_snapshot,
            replay_output=output_snapshot,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=TEST_CORPUS_ID,
        )
        assert detail_view.input_hash == "SHA256:abc123def456"

    def test_invalid_input_hash_no_algorithm_prefix(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash without algorithm prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="abc123def456",  # Missing algorithm prefix
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)
        assert any("algorithm:hexdigest" in str(e["msg"]) for e in errors)

    def test_invalid_input_hash_empty_digest(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash with empty digest is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="sha256:",  # Empty digest
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)

    def test_invalid_input_hash_empty_algorithm(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash with empty algorithm is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash=":abc123",  # Empty algorithm
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)

    def test_invalid_input_hash_non_hex_digest(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash with non-hexadecimal digest is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="sha256:xyz123",  # 'xyz' is not valid hex
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)

    def test_invalid_input_hash_special_chars_in_algorithm(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash with special characters in algorithm is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="sha-256:abc123",  # Hyphen not allowed
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)

    def test_invalid_input_hash_multiple_colons(
        self,
        input_snapshot: ModelInputSnapshot,
        output_snapshot: ModelOutputSnapshot,
        side_by_side: ModelSideBySideComparison,
        timing: ModelTimingBreakdown,
    ) -> None:
        """Input hash with multiple colons is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDetailView(
                comparison_id=TEST_COMPARISON_ID,
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                original_input=input_snapshot,
                input_hash="sha256:abc:123",  # Multiple colons
                input_display="{}",
                baseline_output=output_snapshot,
                replay_output=output_snapshot,
                outputs_match=True,
                side_by_side=side_by_side,
                invariant_results=[],
                invariants_all_passed=True,
                timing_breakdown=timing,
                execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
                corpus_entry_id=TEST_CORPUS_ID,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input_hash",) for e in errors)


@pytest.mark.unit
class TestModelDiffLineEdgeCases:
    """Additional edge case tests for ModelDiffLine."""

    def test_empty_content_strings_valid(self) -> None:
        """Empty strings are valid content."""
        diff_line = ModelDiffLine(
            line_number=1,
            baseline_content="",
            replay_content="",
            change_type="unchanged",
        )
        assert diff_line.baseline_content == ""
        assert diff_line.replay_content == ""

    def test_line_number_zero_rejected(self) -> None:
        """Line number zero is invalid (line numbers are 1-indexed)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=0,
                baseline_content="content",
                replay_content="content",
                change_type="unchanged",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("line_number",)
        assert "greater than or equal to 1" in str(errors[0]["msg"])

    def test_special_characters_in_content(self) -> None:
        """Special characters in content are preserved."""
        content_with_special = '{\n\t"key": "value",\n\t"emoji": "🔑"\n}'
        diff_line = ModelDiffLine(
            line_number=1,
            baseline_content=content_with_special,
            replay_content=content_with_special,
            change_type="unchanged",
        )
        assert diff_line.baseline_content == content_with_special
        assert "🔑" in diff_line.baseline_content


@pytest.mark.unit
class TestModelPhaseTimeEdgeCases:
    """Additional edge case tests for ModelPhaseTime."""

    def test_zero_times_valid(self) -> None:
        """Zero millisecond times are valid."""
        phase_time = ModelPhaseTime(
            phase_name="instant_phase",
            baseline_ms=0.0,
            replay_ms=0.0,
            delta_percent=0.0,
        )
        assert phase_time.baseline_ms == 0.0
        assert phase_time.replay_ms == 0.0

    def test_very_large_times_valid(self) -> None:
        """Very large time values are valid."""
        phase_time = ModelPhaseTime(
            phase_name="long_running",
            baseline_ms=1000000.0,  # ~16 minutes
            replay_ms=1500000.0,  # ~25 minutes
            delta_percent=50.0,
        )
        assert phase_time.baseline_ms == 1000000.0

    def test_fractional_milliseconds_valid(self) -> None:
        """Fractional milliseconds are preserved."""
        phase_time = ModelPhaseTime(
            phase_name="precise_phase",
            baseline_ms=0.123456,
            replay_ms=0.234567,
            delta_percent=90.0,
        )
        assert phase_time.baseline_ms == 0.123456
        assert phase_time.replay_ms == 0.234567


@pytest.mark.unit
class TestModelSnapshotEdgeCases:
    """Additional edge case tests for snapshot models."""

    def test_empty_raw_dict_valid_for_input(self) -> None:
        """Empty raw dictionary is valid for input snapshot."""
        snapshot = ModelInputSnapshot(
            raw={},
            original_size_bytes=2,  # "{}" is 2 bytes
            display_size_bytes=2,
        )
        assert snapshot.raw == {}

    def test_empty_raw_dict_valid_for_output(self) -> None:
        """Empty raw dictionary is valid for output snapshot."""
        snapshot = ModelOutputSnapshot(
            raw={},
            original_size_bytes=2,
            display_size_bytes=2,
            output_hash="sha256:1234567890ab",
        )
        assert snapshot.raw == {}

    def test_nested_raw_data_preserved(self) -> None:
        """Nested data structures are preserved in raw."""
        nested_data: dict[str, Any] = {
            "level1": {
                "level2": {
                    "level3": [1, 2, {"level4": "deep_value"}],
                },
            },
        }
        snapshot = ModelInputSnapshot(
            raw=nested_data,
            original_size_bytes=500,
            display_size_bytes=500,
        )
        assert snapshot.raw["level1"]["level2"]["level3"][2]["level4"] == "deep_value"


@pytest.mark.unit
class TestModelExecutionDetailViewSerialization:
    """Test serialization of ModelExecutionDetailView."""

    def test_model_dump_returns_complete_dict(self) -> None:
        """model_dump returns complete dictionary representation."""
        comparison_id = UUID("1234567b-1234-5678-1234-567812345678")
        baseline_id = UUID("2234567b-1234-5678-1234-567812345678")
        replay_id = UUID("3234567b-1234-5678-1234-567812345678")
        corpus_id = UUID("4234567b-1234-5678-1234-567812345678")
        input_snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
        )
        output_snapshot = ModelOutputSnapshot(
            raw={"result": "data"},
            original_size_bytes=60,
            display_size_bytes=60,
            output_hash="sha256:abc123",
        )
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        timing = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=input_snapshot,
            input_hash="sha256:fedcba654321",
            input_display="{}",
            baseline_output=output_snapshot,
            replay_output=output_snapshot,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=corpus_id,
        )

        data = detail_view.model_dump()

        assert isinstance(data, dict)
        assert data["comparison_id"] == comparison_id
        assert data["outputs_match"] is True
        assert isinstance(data["original_input"], dict)
        assert isinstance(data["timing_breakdown"], dict)
        assert data["invariants_all_passed"] is True

    def test_model_dump_json_returns_valid_json(self) -> None:
        """model_dump_json returns valid JSON string."""
        comparison_id = UUID("1234567c-1234-5678-1234-567812345678")
        baseline_id = UUID("2234567c-1234-5678-1234-567812345678")
        replay_id = UUID("3234567c-1234-5678-1234-567812345678")
        corpus_id = UUID("4234567c-1234-5678-1234-567812345678")
        input_snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
        )
        output_snapshot = ModelOutputSnapshot(
            raw={"result": "data"},
            original_size_bytes=60,
            display_size_bytes=60,
            output_hash="sha256:abc123",
        )
        side_by_side = ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )
        timing = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=input_snapshot,
            input_hash="sha256:fedcba654321",
            input_display="{}",
            baseline_output=output_snapshot,
            replay_output=output_snapshot,
            outputs_match=True,
            side_by_side=side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=timing,
            execution_timestamp=datetime(2025, 1, 4, 12, 0, 0, tzinfo=UTC),
            corpus_entry_id=corpus_id,
        )

        json_str = detail_view.model_dump_json()

        assert isinstance(json_str, str)
        # UUID is serialized as string in JSON
        assert '"comparison_id":"1234567c-1234-5678-1234-567812345678"' in json_str
        assert '"outputs_match":true' in json_str


@pytest.mark.unit
class TestModelExecutionDetailViewEdgeCases:
    """Edge case tests for ModelExecutionDetailView.

    These tests verify the behavior documented in the Validation section
    of the ModelExecutionDetailView docstring.
    """

    @pytest.fixture
    def minimal_input_snapshot(self) -> ModelInputSnapshot:
        """Provide minimal input snapshot for edge case tests."""
        return ModelInputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
        )

    @pytest.fixture
    def minimal_output_snapshot(self) -> ModelOutputSnapshot:
        """Provide minimal output snapshot for edge case tests."""
        return ModelOutputSnapshot(
            raw={"result": "data"},
            original_size_bytes=60,
            display_size_bytes=60,
            output_hash="sha256:abc123def456",
        )

    @pytest.fixture
    def minimal_side_by_side(self) -> ModelSideBySideComparison:
        """Provide minimal side-by-side comparison for edge case tests."""
        return ModelSideBySideComparison(
            baseline_formatted="{}",
            replay_formatted="{}",
            diff_lines=[],
        )

    @pytest.fixture
    def minimal_timing(self) -> ModelTimingBreakdown:
        """Provide minimal timing breakdown for edge case tests."""
        return ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )

    def test_empty_invariant_results_valid(
        self,
        minimal_input_snapshot: ModelInputSnapshot,
        minimal_output_snapshot: ModelOutputSnapshot,
        minimal_side_by_side: ModelSideBySideComparison,
        minimal_timing: ModelTimingBreakdown,
    ) -> None:
        """Verify empty invariant_results list is valid.

        This tests the documented behavior that invariant_results can be
        an empty list for executions with no invariant checks configured.
        """
        comparison_id = UUID("aaaaaaaa-1111-2222-3333-444444444444")
        baseline_id = UUID("bbbbbbbb-1111-2222-3333-444444444444")
        replay_id = UUID("cccccccc-1111-2222-3333-444444444444")
        corpus_id = UUID("dddddddd-1111-2222-3333-444444444444")

        # Should not raise - empty invariant_results is valid
        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=minimal_input_snapshot,
            input_hash="sha256:aaaa1111bbbb2222",
            input_display='{"key": "value"}',
            baseline_output=minimal_output_snapshot,
            replay_output=minimal_output_snapshot,
            outputs_match=True,
            side_by_side=minimal_side_by_side,
            invariant_results=[],  # Empty list is valid
            invariants_all_passed=True,
            timing_breakdown=minimal_timing,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )

        assert detail_view.invariant_results == []
        assert len(detail_view.invariant_results) == 0

    def test_invariants_all_passed_consistency_with_empty_results(
        self,
        minimal_input_snapshot: ModelInputSnapshot,
        minimal_output_snapshot: ModelOutputSnapshot,
        minimal_side_by_side: ModelSideBySideComparison,
        minimal_timing: ModelTimingBreakdown,
    ) -> None:
        """Test that invariants_all_passed can be True with empty list.

        When invariant_results is empty, invariants_all_passed should typically
        be True (vacuously true - no invariants means none failed).
        """
        comparison_id = UUID("eeeeeeee-1111-2222-3333-444444444444")
        baseline_id = UUID("ffffffff-1111-2222-3333-444444444444")
        replay_id = UUID("00000000-1111-2222-3333-444444444444")
        corpus_id = UUID("11111111-1111-2222-3333-444444444444")

        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=minimal_input_snapshot,
            input_hash="sha256:cccc3333dddd4444",
            input_display='{"test": "data"}',
            baseline_output=minimal_output_snapshot,
            replay_output=minimal_output_snapshot,
            outputs_match=True,
            side_by_side=minimal_side_by_side,
            invariant_results=[],  # No invariants configured
            invariants_all_passed=True,  # Vacuously true
            timing_breakdown=minimal_timing,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )

        # With no invariants, all passed is vacuously true
        assert detail_view.invariant_results == []
        assert detail_view.invariants_all_passed is True

    def test_input_display_can_differ_from_raw(
        self,
        minimal_output_snapshot: ModelOutputSnapshot,
        minimal_side_by_side: ModelSideBySideComparison,
        minimal_timing: ModelTimingBreakdown,
    ) -> None:
        """Show that input_display is independent from original_input.raw.

        input_display is a convenience field for UI display and may contain
        a truncated representation. For canonical data, use original_input.raw.
        """
        comparison_id = UUID("22222222-1111-2222-3333-444444444444")
        baseline_id = UUID("33333333-1111-2222-3333-444444444444")
        replay_id = UUID("44444444-1111-2222-3333-444444444444")
        corpus_id = UUID("55555555-1111-2222-3333-444444444444")

        # Create input snapshot with full data
        full_raw_data: dict[str, Any] = {
            "prompt": "This is a very long prompt that would be truncated in display",
            "parameters": {"temperature": 0.7, "max_tokens": 100},
            "metadata": {"user_id": "user123", "session_id": "session456"},
        }
        input_snapshot = ModelInputSnapshot(
            raw=full_raw_data,
            truncated=False,
            original_size_bytes=500,
            display_size_bytes=500,
        )

        # input_display can be a truncated/formatted version
        truncated_display = '{"prompt": "This is a very long..."}'

        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=input_snapshot,
            input_hash="sha256:eeee5555ffff6666",
            input_display=truncated_display,  # Truncated for UI
            baseline_output=minimal_output_snapshot,
            replay_output=minimal_output_snapshot,
            outputs_match=True,
            side_by_side=minimal_side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=minimal_timing,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )

        # input_display differs from original_input.raw
        assert detail_view.input_display != str(detail_view.original_input.raw)
        # Canonical data is in original_input.raw
        assert detail_view.original_input.raw == full_raw_data
        # Display is truncated
        assert "..." in detail_view.input_display

    def test_large_input_display_accepted(
        self,
        minimal_input_snapshot: ModelInputSnapshot,
        minimal_output_snapshot: ModelOutputSnapshot,
        minimal_side_by_side: ModelSideBySideComparison,
        minimal_timing: ModelTimingBreakdown,
    ) -> None:
        """Very large input_display string works without issues."""
        comparison_id = UUID("66666666-1111-2222-3333-444444444444")
        baseline_id = UUID("77777777-1111-2222-3333-444444444444")
        replay_id = UUID("88888888-1111-2222-3333-444444444444")
        corpus_id = UUID("99999999-1111-2222-3333-444444444444")

        # Create a very large input display string (100KB)
        large_content = "x" * 100_000
        large_input_display = f'{{"large_data": "{large_content}"}}'

        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=minimal_input_snapshot,
            input_hash="sha256:1122334455667788",
            input_display=large_input_display,
            baseline_output=minimal_output_snapshot,
            replay_output=minimal_output_snapshot,
            outputs_match=True,
            side_by_side=minimal_side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=minimal_timing,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )

        assert len(detail_view.input_display) > 100_000
        assert large_content in detail_view.input_display

    def test_unicode_in_input_display(
        self,
        minimal_input_snapshot: ModelInputSnapshot,
        minimal_output_snapshot: ModelOutputSnapshot,
        minimal_side_by_side: ModelSideBySideComparison,
        minimal_timing: ModelTimingBreakdown,
    ) -> None:
        """Unicode characters are preserved in input_display."""
        comparison_id = UUID("aaaaaaaa-2222-3333-4444-555555555555")
        baseline_id = UUID("bbbbbbbb-2222-3333-4444-555555555555")
        replay_id = UUID("cccccccc-2222-3333-4444-555555555555")
        corpus_id = UUID("dddddddd-2222-3333-4444-555555555555")

        # Input display with various Unicode characters
        unicode_input_display = (
            '{"message": "Hello, World! Bonjour! Hallo!", '
            '"emoji": "Test: check_mark sword fire rocket", '
            '"cjk": "Chinese Japanese Korean characters", '
            '"arabic": "Arabic text sample", '
            '"math": "Mathematical symbols: sum integral infinity"}'
        )

        detail_view = ModelExecutionDetailView(
            comparison_id=comparison_id,
            baseline_execution_id=baseline_id,
            replay_execution_id=replay_id,
            original_input=minimal_input_snapshot,
            input_hash="sha256:99aabbccddee00",
            input_display=unicode_input_display,
            baseline_output=minimal_output_snapshot,
            replay_output=minimal_output_snapshot,
            outputs_match=True,
            side_by_side=minimal_side_by_side,
            invariant_results=[],
            invariants_all_passed=True,
            timing_breakdown=minimal_timing,
            execution_timestamp=datetime.now(UTC),
            corpus_entry_id=corpus_id,
        )

        # All Unicode content is preserved
        assert "Hello, World!" in detail_view.input_display
        assert "Bonjour" in detail_view.input_display
        assert "emoji" in detail_view.input_display
        assert "cjk" in detail_view.input_display
        assert "arabic" in detail_view.input_display
        assert "math" in detail_view.input_display
