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
                change_type="invalid_type",
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
            output_hash="sha256:full_output_hash_xyz789",
        )
        assert snapshot.truncated is True
        assert snapshot.output_hash == "sha256:full_output_hash_xyz789"

    def test_default_truncated_false(self) -> None:
        """Default value for truncated is False."""
        snapshot = ModelOutputSnapshot(
            raw={"output": "data"},
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:hash",
        )
        assert snapshot.truncated is False

    def test_frozen_immutable(self) -> None:
        """Model is immutable (frozen)."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            original_size_bytes=50,
            display_size_bytes=50,
            output_hash="sha256:test_hash",
        )
        with pytest.raises(ValidationError):
            snapshot.output_hash = "sha256:modified_hash"
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
                status_change="invalid_status",
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
            output_hash="sha256:baseline_hash_abc123",
        )

    @pytest.fixture
    def sample_replay_output(self) -> ModelOutputSnapshot:
        """Provide sample replay output snapshot."""
        return ModelOutputSnapshot(
            raw={"response": "Hello from replay!"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:replay_hash_xyz789",
        )

    @pytest.fixture
    def sample_matching_replay_output(self) -> ModelOutputSnapshot:
        """Provide replay output that matches baseline."""
        return ModelOutputSnapshot(
            raw={"response": "Hello from baseline!"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:baseline_hash_abc123",  # Same hash as baseline
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
            input_hash="sha256:input_hash_abc",
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
            input_hash="sha256:input_hash",
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
            input_hash="sha256:input",
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
            input_hash="sha256:hash",
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
            input_hash="sha256:hash",
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
            input_hash="sha256:hash",
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
            input_hash="sha256:hash",
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
            input_hash="sha256:hash",
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
                self.input_hash = "sha256:attrs_hash"
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

    def test_line_number_zero_valid(self) -> None:
        """Line number zero is valid."""
        diff_line = ModelDiffLine(
            line_number=0,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        assert diff_line.line_number == 0

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
            output_hash="sha256:empty_hash",
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
            output_hash="sha256:hash",
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
            input_hash="sha256:input",
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
            output_hash="sha256:hash",
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
            input_hash="sha256:input",
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
