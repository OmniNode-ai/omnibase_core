# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for corpus replay models (OMN-1204)."""

from uuid import uuid4

import pytest

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.replay import (
    ModelAggregateMetrics,
    ModelCorpusReplayConfig,
    ModelCorpusReplayProgress,
    ModelCorpusReplayResult,
    ModelSingleReplayResult,
    ModelSubsetFilter,
)


class TestModelSubsetFilter:
    """Tests for ModelSubsetFilter."""

    def test_empty_filter_has_no_filters(self) -> None:
        """Empty filter should have has_filters=False."""
        f = ModelSubsetFilter()
        assert not f.has_filters

    def test_handler_filter_has_filters(self) -> None:
        """Handler filter should have has_filters=True."""
        f = ModelSubsetFilter(handler_names=("text-transform",))
        assert f.has_filters

    def test_index_range_filter_has_filters(self) -> None:
        """Index range filter should have has_filters=True."""
        f = ModelSubsetFilter(index_start=0, index_end=10)
        assert f.has_filters

    def test_invalid_index_range_raises(self) -> None:
        """index_start > index_end should raise."""
        with pytest.raises(ModelOnexError):
            ModelSubsetFilter(index_start=10, index_end=5)

    def test_str_representation(self) -> None:
        """String representation should include filter details."""
        f = ModelSubsetFilter(handler_names=("test",), index_start=0, index_end=10)
        s = str(f)
        assert "handlers" in s
        assert "range" in s


class TestModelCorpusReplayConfig:
    """Tests for ModelCorpusReplayConfig."""

    def test_default_config_is_sequential(self) -> None:
        """Default config should be sequential (concurrency=1)."""
        config = ModelCorpusReplayConfig()
        assert config.is_sequential
        assert not config.is_parallel
        assert config.concurrency == 1

    def test_parallel_config(self) -> None:
        """Parallel config should have is_parallel=True."""
        config = ModelCorpusReplayConfig(concurrency=4)
        assert config.is_parallel
        assert not config.is_sequential

    def test_fail_fast_default_is_false(self) -> None:
        """Default fail_fast should be False."""
        config = ModelCorpusReplayConfig()
        assert not config.fail_fast

    def test_config_overrides(self) -> None:
        """Config overrides should be stored."""
        config = ModelCorpusReplayConfig(config_overrides={"timeout_ms": 5000})
        assert config.config_overrides == {"timeout_ms": 5000}

    def test_str_representation(self) -> None:
        """String representation should include mode and error handling."""
        config = ModelCorpusReplayConfig(concurrency=4, fail_fast=True)
        s = str(config)
        assert "parallel" in s
        assert "fail-fast" in s


class TestModelCorpusReplayProgress:
    """Tests for ModelCorpusReplayProgress."""

    def test_remaining_calculation(self) -> None:
        """Remaining should be total - completed - failed - skipped."""
        progress = ModelCorpusReplayProgress(
            total=50, completed=20, failed=5, skipped=5
        )
        assert progress.remaining == 20

    def test_processed_calculation(self) -> None:
        """Processed should be completed + failed + skipped."""
        progress = ModelCorpusReplayProgress(
            total=50, completed=20, failed=5, skipped=5
        )
        assert progress.processed == 30

    def test_completion_percent(self) -> None:
        """Completion percent should be (processed / total) * 100."""
        progress = ModelCorpusReplayProgress(
            total=50, completed=25, failed=0, skipped=0
        )
        assert progress.completion_percent == 50.0

    def test_completion_percent_zero_total(self) -> None:
        """Completion percent with zero total should be 100."""
        progress = ModelCorpusReplayProgress(total=0)
        assert progress.completion_percent == 100.0

    def test_is_complete(self) -> None:
        """is_complete should be True when remaining is 0."""
        progress = ModelCorpusReplayProgress(total=10, completed=8, failed=2, skipped=0)
        assert progress.is_complete


class TestModelSingleReplayResult:
    """Tests for ModelSingleReplayResult."""

    def test_successful_result(self) -> None:
        """Successful result should have is_success=True."""
        result = ModelSingleReplayResult(
            manifest_id=uuid4(), success=True, duration_ms=100.0
        )
        assert result.is_success
        assert not result.is_failure

    def test_failed_result(self) -> None:
        """Failed result should have is_failure=True."""
        result = ModelSingleReplayResult(
            manifest_id=uuid4(),
            success=False,
            duration_ms=50.0,
            error_message="Test error",
            error_type="TestError",
        )
        assert result.is_failure
        assert not result.is_success
        assert result.error_message == "Test error"

    def test_output_mismatch(self) -> None:
        """has_output_mismatch should detect mismatched outputs."""
        result = ModelSingleReplayResult(
            manifest_id=uuid4(),
            success=True,
            duration_ms=100.0,
            outputs_match=False,
        )
        assert result.has_output_mismatch


class TestModelAggregateMetrics:
    """Tests for ModelAggregateMetrics."""

    def test_from_durations_empty(self) -> None:
        """Empty durations should return default metrics."""
        metrics = ModelAggregateMetrics.from_durations(
            durations=[], total_duration_ms=0.0, success_count=0, total_count=0
        )
        assert metrics.avg_duration_ms is None
        assert metrics.p95_duration_ms is None

    def test_from_durations_single(self) -> None:
        """Single duration should have matching avg/min/max."""
        metrics = ModelAggregateMetrics.from_durations(
            durations=[100.0], total_duration_ms=100.0, success_count=1, total_count=1
        )
        assert metrics.avg_duration_ms == 100.0
        assert metrics.min_duration_ms == 100.0
        assert metrics.max_duration_ms == 100.0

    def test_from_durations_multiple(self) -> None:
        """Multiple durations should compute correct percentiles."""
        durations = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        metrics = ModelAggregateMetrics.from_durations(
            durations=durations,
            total_duration_ms=550.0,
            success_count=10,
            total_count=10,
        )
        assert metrics.avg_duration_ms == 55.0
        assert metrics.min_duration_ms == 10.0
        assert metrics.max_duration_ms == 100.0
        assert metrics.success_rate == 1.0
        # P50 should be around 55
        assert metrics.p50_duration_ms is not None
        assert 50.0 <= metrics.p50_duration_ms <= 60.0


class TestModelCorpusReplayResult:
    """Tests for ModelCorpusReplayResult."""

    def test_success_rate(self) -> None:
        """Success rate should be successful / (successful + failed)."""
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=50,
            successful=40,
            failed=10,
            skipped=0,
            duration_ms=5000.0,
        )
        assert result.success_rate == 0.8

    def test_all_successful(self) -> None:
        """all_successful should be True when no failures and not cancelled."""
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=10,
            successful=10,
            failed=0,
            skipped=0,
            duration_ms=1000.0,
        )
        assert result.all_successful

    def test_all_successful_false_with_failures(self) -> None:
        """all_successful should be False when there are failures."""
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=10,
            successful=9,
            failed=1,
            skipped=0,
            duration_ms=1000.0,
        )
        assert not result.all_successful

    def test_all_successful_false_when_cancelled(self) -> None:
        """all_successful should be False when cancelled."""
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=10,
            successful=5,
            failed=0,
            skipped=5,
            duration_ms=1000.0,
            was_cancelled=True,
        )
        assert not result.all_successful

    def test_is_complete(self) -> None:
        """is_complete should be True when all processed."""
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=10,
            successful=8,
            failed=2,
            skipped=0,
            duration_ms=1000.0,
        )
        assert result.is_complete

    def test_invalid_counts_raises(self) -> None:
        """Counts exceeding total should raise."""
        with pytest.raises(ModelOnexError):
            ModelCorpusReplayResult(
                corpus_id=uuid4(),
                corpus_name="test",
                total_executions=10,
                successful=8,
                failed=5,  # 8 + 5 = 13 > 10
                skipped=0,
                duration_ms=1000.0,
            )

    def test_get_failed_results(self) -> None:
        """get_failed_results should return only failed results."""
        failed_result = ModelSingleReplayResult(
            manifest_id=uuid4(), success=False, duration_ms=50.0
        )
        success_result = ModelSingleReplayResult(
            manifest_id=uuid4(), success=True, duration_ms=100.0
        )
        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="test",
            total_executions=2,
            successful=1,
            failed=1,
            skipped=0,
            execution_results=(success_result, failed_result),
            duration_ms=150.0,
        )
        failed = result.get_failed_results()
        assert len(failed) == 1
        assert failed[0].manifest_id == failed_result.manifest_id
