"""Tests for ModelBaselineHealthReport - Baseline Health Report feature (OMN-1198).

This test module tests the baseline health report models:
- ModelInvariantStatus: Status of individual invariant checks
- ModelPerformanceMetrics: Performance metrics observations
- ModelBaselineHealthReport: Comprehensive health snapshot
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.health.model_baseline_health_report import (
    ModelBaselineHealthReport,
)
from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.types.typed_dict_system_config import TypedDictSystemConfig

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def passing_invariant() -> ModelInvariantStatus:
    """Create a passing invariant status."""
    return ModelInvariantStatus(
        invariant_id=uuid4(),
        name="output_format_valid",
        passed=True,
        details="All outputs match expected format",
    )


@pytest.fixture
def failing_invariant() -> ModelInvariantStatus:
    """Create a failing invariant status."""
    return ModelInvariantStatus(
        invariant_id=uuid4(),
        name="response_time_within_limit",
        passed=False,
        details="Response exceeded 5000ms threshold",
    )


@pytest.fixture
def healthy_metrics() -> ModelPerformanceMetrics:
    """Create healthy performance metrics."""
    return ModelPerformanceMetrics(
        avg_latency_ms=150.0,
        p95_latency_ms=350.0,
        p99_latency_ms=500.0,
        avg_cost_per_call=0.002,
        total_calls=10000,
        error_rate=0.01,
    )


@pytest.fixture
def degraded_metrics() -> ModelPerformanceMetrics:
    """Create degraded performance metrics."""
    return ModelPerformanceMetrics(
        avg_latency_ms=800.0,
        p95_latency_ms=2000.0,
        p99_latency_ms=5000.0,
        avg_cost_per_call=0.005,
        total_calls=5000,
        error_rate=0.15,
    )


@pytest.fixture
def sample_report(
    passing_invariant: ModelInvariantStatus,
    healthy_metrics: ModelPerformanceMetrics,
    sample_config: TypedDictSystemConfig,
) -> ModelBaselineHealthReport:
    """Create a sample baseline health report."""
    config_str = json.dumps(sample_config, sort_keys=True)
    config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]

    return ModelBaselineHealthReport(
        report_id=uuid4(),
        generated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        current_config=sample_config,  # type: ignore[arg-type]
        config_hash=config_hash,
        corpus_size=1000,
        corpus_date_range=(
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 14, tzinfo=UTC),
        ),
        input_diversity_score=0.85,
        invariants_checked=[passing_invariant],
        all_invariants_passing=True,
        metrics=healthy_metrics,
        stability_score=0.92,
        stability_status="stable",
        stability_details="All metrics within acceptable ranges",
        confidence_level=0.95,
        confidence_reasoning="Large corpus size with high diversity",
    )


# ============================================================================
# ModelInvariantStatus Tests
# ============================================================================


@pytest.mark.unit
class TestModelInvariantStatus:
    """Test ModelInvariantStatus model."""

    def test_basic_initialization(
        self, passing_invariant: ModelInvariantStatus
    ) -> None:
        """Test basic invariant status creation."""
        assert passing_invariant.name == "output_format_valid"
        assert passing_invariant.passed is True
        assert passing_invariant.details is not None

    def test_failing_invariant(self, failing_invariant: ModelInvariantStatus) -> None:
        """Test failing invariant status."""
        assert failing_invariant.passed is False
        assert failing_invariant.details is not None
        assert "exceeded" in failing_invariant.details.lower()

    def test_invariant_id_is_uuid(self) -> None:
        """Test that invariant_id must be a UUID."""
        invariant = ModelInvariantStatus(
            invariant_id=uuid4(),
            name="test",
            passed=True,
        )
        assert invariant.invariant_id is not None

    def test_optional_details(self) -> None:
        """Test that details field is optional."""
        invariant = ModelInvariantStatus(
            invariant_id=uuid4(),
            name="test_invariant",
            passed=True,
        )
        assert invariant.details is None

    def test_frozen_model(self, passing_invariant: ModelInvariantStatus) -> None:
        """Test that model is immutable."""
        with pytest.raises(ValidationError):
            passing_invariant.passed = False  # type: ignore[misc]


# ============================================================================
# ModelPerformanceMetrics Tests
# ============================================================================


@pytest.mark.unit
class TestModelPerformanceMetrics:
    """Test ModelPerformanceMetrics model."""

    def test_basic_initialization(
        self, healthy_metrics: ModelPerformanceMetrics
    ) -> None:
        """Test basic metrics creation."""
        assert healthy_metrics.avg_latency_ms == 150.0
        assert healthy_metrics.error_rate == 0.01

    def test_degraded_metrics(self, degraded_metrics: ModelPerformanceMetrics) -> None:
        """Test degraded metrics values."""
        assert degraded_metrics.avg_latency_ms == 800.0
        assert degraded_metrics.error_rate == 0.15

    def test_validation_negative_latency(self) -> None:
        """Test validation rejects negative latency."""
        with pytest.raises(ValidationError):
            ModelPerformanceMetrics(
                avg_latency_ms=-100.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=0.01,
            )

    def test_validation_error_rate_bounds(self) -> None:
        """Test error rate must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=200.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=1.5,  # Invalid: > 1
            )


# ============================================================================
# ModelBaselineHealthReport Tests
# ============================================================================


@pytest.mark.unit
class TestModelBaselineHealthReport:
    """Test ModelBaselineHealthReport model."""

    def test_basic_initialization(
        self, sample_report: ModelBaselineHealthReport
    ) -> None:
        """Test basic report creation."""
        assert sample_report.report_id is not None
        assert sample_report.stability_status == "stable"
        assert sample_report.stability_score == 0.92

    def test_is_stable_method(self, sample_report: ModelBaselineHealthReport) -> None:
        """Test is_stable helper method."""
        assert sample_report.is_stable() is True

    def test_is_safe_for_changes_method(
        self, sample_report: ModelBaselineHealthReport
    ) -> None:
        """Test is_safe_for_changes helper method."""
        assert sample_report.is_safe_for_changes() is True

    def test_get_failing_invariants_empty(
        self, sample_report: ModelBaselineHealthReport
    ) -> None:
        """Test get_failing_invariants returns empty list when all pass."""
        failing = sample_report.get_failing_invariants()
        assert len(failing) == 0

    def test_stability_score_bounds(self) -> None:
        """Test stability score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ModelBaselineHealthReport(
                report_id=uuid4(),
                generated_at=datetime.now(UTC),
                current_config={},  # type: ignore[arg-type]
                config_hash="test",
                corpus_size=100,
                corpus_date_range=(
                    datetime(2024, 1, 1, tzinfo=UTC),
                    datetime(2024, 1, 14, tzinfo=UTC),
                ),
                input_diversity_score=0.5,
                invariants_checked=[],
                all_invariants_passing=True,
                metrics=ModelPerformanceMetrics(
                    avg_latency_ms=100.0,
                    p95_latency_ms=200.0,
                    p99_latency_ms=300.0,
                    avg_cost_per_call=0.002,
                    total_calls=1000,
                    error_rate=0.01,
                ),
                stability_score=1.5,  # Invalid: > 1.0
                stability_status="stable",
                stability_details="test",
                confidence_level=0.8,
                confidence_reasoning="test",
            )


# ============================================================================
# Date Range Validation Tests
# ============================================================================


@pytest.mark.unit
class TestDateRangeValidation:
    """Test corpus_date_range ordering validation."""

    def test_valid_date_range_start_before_end(
        self,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Test that valid date range (start < end) is accepted."""
        report = ModelBaselineHealthReport(
            report_id=uuid4(),
            generated_at=datetime.now(UTC),
            current_config={},  # type: ignore[arg-type]
            config_hash="test",
            corpus_size=100,
            corpus_date_range=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 31, tzinfo=UTC),
            ),
            input_diversity_score=0.5,
            invariants_checked=[],
            all_invariants_passing=True,
            metrics=healthy_metrics,
            stability_score=0.8,
            stability_status="stable",
            stability_details="test",
            confidence_level=0.8,
            confidence_reasoning="test",
        )
        assert report.corpus_date_range[0] < report.corpus_date_range[1]

    def test_invalid_date_range_start_equals_end(
        self,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Test that equal start and end dates raise ModelOnexError."""
        same_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBaselineHealthReport(
                report_id=uuid4(),
                generated_at=datetime.now(UTC),
                current_config={},  # type: ignore[arg-type]
                config_hash="test",
                corpus_size=100,
                corpus_date_range=(same_time, same_time),
                input_diversity_score=0.5,
                invariants_checked=[],
                all_invariants_passing=True,
                metrics=healthy_metrics,
                stability_score=0.8,
                stability_status="stable",
                stability_details="test",
                confidence_level=0.8,
                confidence_reasoning="test",
            )

        assert "corpus_date_range start must be before end" in str(exc_info.value)
        assert exc_info.value.context is not None
        additional_context = exc_info.value.context.get("additional_context", {})
        assert "start" in additional_context
        assert "end" in additional_context

    def test_invalid_date_range_start_after_end(
        self,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Test that start > end raises ModelOnexError."""
        start = datetime(2024, 1, 31, tzinfo=UTC)
        end = datetime(2024, 1, 1, tzinfo=UTC)
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBaselineHealthReport(
                report_id=uuid4(),
                generated_at=datetime.now(UTC),
                current_config={},  # type: ignore[arg-type]
                config_hash="test",
                corpus_size=100,
                corpus_date_range=(start, end),
                input_diversity_score=0.5,
                invariants_checked=[],
                all_invariants_passing=True,
                metrics=healthy_metrics,
                stability_score=0.8,
                stability_status="stable",
                stability_details="test",
                confidence_level=0.8,
                confidence_reasoning="test",
            )

        assert "corpus_date_range start must be before end" in str(exc_info.value)
        # Verify context contains actual dates
        assert exc_info.value.context is not None
        additional_context = exc_info.value.context.get("additional_context", {})
        assert additional_context["start"] == start.isoformat()
        assert additional_context["end"] == end.isoformat()

    def test_date_range_error_includes_context(
        self,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Test that error context includes ISO-formatted dates."""
        start = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)
        end = datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelBaselineHealthReport(
                report_id=uuid4(),
                generated_at=datetime.now(UTC),
                current_config={},  # type: ignore[arg-type]
                config_hash="test",
                corpus_size=100,
                corpus_date_range=(start, end),
                input_diversity_score=0.5,
                invariants_checked=[],
                all_invariants_passing=True,
                metrics=healthy_metrics,
                stability_score=0.8,
                stability_status="stable",
                stability_details="test",
                confidence_level=0.8,
                confidence_reasoning="test",
            )

        # Verify ISO format in context
        assert exc_info.value.context is not None
        additional_context = exc_info.value.context.get("additional_context", {})
        assert "2024-06-15" in additional_context["start"]
        assert "2024-06-01" in additional_context["end"]


# ============================================================================
# Health Calculation Tests
# ============================================================================


@pytest.fixture
def high_error_metrics() -> ModelPerformanceMetrics:
    """Create metrics with high error rate (>5%)."""
    return ModelPerformanceMetrics(
        avg_latency_ms=100.0,
        p95_latency_ms=200.0,
        p99_latency_ms=300.0,
        avg_cost_per_call=0.002,
        total_calls=1000,
        error_rate=0.10,  # 10% error rate
    )


@pytest.fixture
def spike_latency_metrics() -> ModelPerformanceMetrics:
    """Create metrics with latency spike (p99 > 2x avg)."""
    return ModelPerformanceMetrics(
        avg_latency_ms=100.0,
        p95_latency_ms=400.0,
        p99_latency_ms=500.0,  # 5x avg - indicates spike
        avg_cost_per_call=0.002,
        total_calls=1000,
        error_rate=0.01,
    )


@pytest.mark.unit
class TestHealthCalculation:
    """Test health calculation logic."""

    def test_all_invariants_passing_sets_flag(
        self,
        passing_invariant: ModelInvariantStatus,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """all_invariants_passing is True only if ALL pass."""
        invariants = [passing_invariant]
        all_passing = all(inv.passed for inv in invariants)

        report = ModelBaselineHealthReport(
            report_id=uuid4(),
            generated_at=datetime.now(UTC),
            current_config={},  # type: ignore[arg-type]
            config_hash="test",
            corpus_size=100,
            corpus_date_range=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 14, tzinfo=UTC),
            ),
            input_diversity_score=0.5,
            invariants_checked=invariants,
            all_invariants_passing=all_passing,
            metrics=healthy_metrics,
            stability_score=0.8,
            stability_status="stable",
            stability_details="test",
            confidence_level=0.8,
            confidence_reasoning="test",
        )

        assert report.all_invariants_passing is True

    def test_single_failing_invariant_flags_unhealthy(
        self,
        passing_invariant: ModelInvariantStatus,
        failing_invariant: ModelInvariantStatus,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """One failing invariant = not healthy."""
        invariants = [passing_invariant, failing_invariant]
        all_passing = all(inv.passed for inv in invariants)

        report = ModelBaselineHealthReport(
            report_id=uuid4(),
            generated_at=datetime.now(UTC),
            current_config={},  # type: ignore[arg-type]
            config_hash="test",
            corpus_size=100,
            corpus_date_range=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 14, tzinfo=UTC),
            ),
            input_diversity_score=0.5,
            invariants_checked=invariants,
            all_invariants_passing=all_passing,
            metrics=healthy_metrics,
            stability_score=0.3,
            stability_status="unstable",
            stability_details="Failing invariant",
            confidence_level=0.8,
            confidence_reasoning="test",
        )

        assert report.all_invariants_passing is False

    def test_error_rate_above_threshold_flags_unstable(
        self,
        passing_invariant: ModelInvariantStatus,
        high_error_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Error rate > 5% should result in unstable status."""
        assert high_error_metrics.error_rate > 0.05

        report = ModelBaselineHealthReport(
            report_id=uuid4(),
            generated_at=datetime.now(UTC),
            current_config={},  # type: ignore[arg-type]
            config_hash="test",
            corpus_size=100,
            corpus_date_range=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 14, tzinfo=UTC),
            ),
            input_diversity_score=0.5,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=high_error_metrics,
            stability_score=0.4,
            stability_status="unstable",
            stability_details="High error rate",
            confidence_level=0.8,
            confidence_reasoning="test",
        )

        assert report.stability_status == "unstable"

    def test_latency_spike_flags_degraded(
        self,
        passing_invariant: ModelInvariantStatus,
        spike_latency_metrics: ModelPerformanceMetrics,
    ) -> None:
        """p99 > 2x avg indicates degraded performance."""
        latency_ratio = (
            spike_latency_metrics.p99_latency_ms / spike_latency_metrics.avg_latency_ms
        )
        assert latency_ratio > 2.0

        report = ModelBaselineHealthReport(
            report_id=uuid4(),
            generated_at=datetime.now(UTC),
            current_config={},  # type: ignore[arg-type]
            config_hash="test",
            corpus_size=1000,
            corpus_date_range=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 14, tzinfo=UTC),
            ),
            input_diversity_score=0.8,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=spike_latency_metrics,
            stability_score=0.65,
            stability_status="degraded",
            stability_details="Latency spikes detected",
            confidence_level=0.9,
            confidence_reasoning="Large corpus",
        )

        assert report.stability_status == "degraded"


# ============================================================================
# Report Generation Tests (Phase 3)
# ============================================================================


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation and serialization."""

    def test_report_includes_all_required_fields(
        self,
        sample_report: ModelBaselineHealthReport,
    ) -> None:
        """Generated report has all fields populated."""
        assert sample_report.report_id is not None
        assert sample_report.generated_at is not None
        assert sample_report.current_config is not None
        assert sample_report.config_hash is not None
        assert sample_report.corpus_size is not None
        assert sample_report.metrics is not None
        assert sample_report.stability_status is not None

    def test_config_hash_is_deterministic(self) -> None:
        """Same config should produce same hash."""
        config = {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000}

        config_str = json.dumps(config, sort_keys=True)
        hash1 = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(config_str.encode()).hexdigest()[:16]

        assert hash1 == hash2

        # Different config should produce different hash
        config2 = {"model": "gpt-3.5-turbo", "temperature": 0.7}
        config_str2 = json.dumps(config2, sort_keys=True)
        hash3 = hashlib.sha256(config_str2.encode()).hexdigest()[:16]

        assert hash1 != hash3

    def test_report_serializes_to_json(
        self,
        sample_report: ModelBaselineHealthReport,
    ) -> None:
        """Report can be serialized for storage."""
        json_str = sample_report.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

        # Key fields should be present
        assert "report_id" in parsed
        assert "stability_status" in parsed
        assert "metrics" in parsed

    def test_report_serializes_to_dict(
        self,
        sample_report: ModelBaselineHealthReport,
    ) -> None:
        """Report can be converted to dictionary."""
        report_dict = sample_report.model_dump()

        assert isinstance(report_dict, dict)
        assert report_dict["stability_status"] == sample_report.stability_status

        # Nested objects should also be dicts
        assert isinstance(report_dict["metrics"], dict)

    def test_report_equality(
        self,
        passing_invariant: ModelInvariantStatus,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Two reports with same data should be equal."""
        common_id = uuid4()
        common_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        common_range = (
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 14, tzinfo=UTC),
        )
        common_config = {"model": "gpt-4", "temperature": 0.7}

        report1 = ModelBaselineHealthReport(
            report_id=common_id,
            generated_at=common_time,
            current_config=common_config,  # type: ignore[arg-type]
            config_hash="hash123",
            corpus_size=100,
            corpus_date_range=common_range,
            input_diversity_score=0.8,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=healthy_metrics,
            stability_score=0.9,
            stability_status="stable",
            stability_details="test",
            confidence_level=0.85,
            confidence_reasoning="test",
        )

        report2 = ModelBaselineHealthReport(
            report_id=common_id,
            generated_at=common_time,
            current_config=common_config,  # type: ignore[arg-type]
            config_hash="hash123",
            corpus_size=100,
            corpus_date_range=common_range,
            input_diversity_score=0.8,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=healthy_metrics,
            stability_score=0.9,
            stability_status="stable",
            stability_details="test",
            confidence_level=0.85,
            confidence_reasoning="test",
        )

        assert report1 == report2


@pytest.mark.unit
class TestReportIdempotency:
    """Test that report generation is idempotent."""

    def test_same_inputs_produce_same_report(
        self,
        passing_invariant: ModelInvariantStatus,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Same inputs should produce identical report."""
        fixed_id = uuid4()
        fixed_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        fixed_range = (
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 14, tzinfo=UTC),
        )
        fixed_config: dict[str, str] = {"model": "test"}

        report1 = ModelBaselineHealthReport(
            report_id=fixed_id,
            generated_at=fixed_time,
            current_config=fixed_config,  # type: ignore[arg-type]
            config_hash="fixed-hash",
            corpus_size=1000,
            corpus_date_range=fixed_range,
            input_diversity_score=0.85,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=healthy_metrics,
            stability_score=0.9,
            stability_status="stable",
            stability_details="Idempotent test",
            confidence_level=0.95,
            confidence_reasoning="Fixed inputs",
        )

        report2 = ModelBaselineHealthReport(
            report_id=fixed_id,
            generated_at=fixed_time,
            current_config=fixed_config,  # type: ignore[arg-type]
            config_hash="fixed-hash",
            corpus_size=1000,
            corpus_date_range=fixed_range,
            input_diversity_score=0.85,
            invariants_checked=[passing_invariant],
            all_invariants_passing=True,
            metrics=healthy_metrics,
            stability_score=0.9,
            stability_status="stable",
            stability_details="Idempotent test",
            confidence_level=0.95,
            confidence_reasoning="Fixed inputs",
        )

        assert report1 == report2
        assert report1.model_dump() == report2.model_dump()
