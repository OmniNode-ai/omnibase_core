# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelCostStatistics."""

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestCostStatisticsCreation:
    """Test model instantiation."""

    def test_create_with_all_fields(self):
        """Create model with all required fields."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=142.0,
            delta_total=42.0,
            delta_percent=42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=14.2,
        )

        assert stats.baseline_total == 100.0
        assert stats.replay_total == 142.0
        assert stats.delta_total == 42.0
        assert stats.delta_percent == 42.0
        assert stats.baseline_avg_per_execution == 10.0
        assert stats.replay_avg_per_execution == 14.2

    def test_immutable_after_creation(self):
        """Model should be frozen (immutable)."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=142.0,
            delta_total=42.0,
            delta_percent=42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=14.2,
        )

        with pytest.raises(ValidationError):
            stats.baseline_total = 200.0  # type: ignore[misc]


@pytest.mark.unit
class TestDeltaCalculations:
    """Test delta calculations."""

    def test_delta_total_positive_increase(self):
        """Positive delta when replay costs more."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        # baseline_total=100, replay_total=142 -> delta_total=42
        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=142.0,
            delta_total=42.0,
            delta_percent=42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=14.2,
        )

        assert stats.delta_total == 42.0
        assert stats.delta_total > 0  # Replay costs more

    def test_delta_total_negative_savings(self):
        """Negative delta when replay costs less."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        # baseline_total=100, replay_total=58 -> delta_total=-42
        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=58.0,
            delta_total=-42.0,
            delta_percent=-42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=5.8,
        )

        assert stats.delta_total == -42.0
        assert stats.delta_total < 0  # Replay costs less (savings)

    def test_delta_percent_calculation(self):
        """Delta percent calculated correctly."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        # baseline=100, replay=58 -> delta_percent=-42.0
        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=58.0,
            delta_total=-42.0,
            delta_percent=-42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=5.8,
        )

        assert stats.delta_percent == -42.0

    def test_delta_percent_with_zero_baseline(self):
        """Handle zero baseline gracefully."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        # Zero baseline should result in inf or a special value for percent
        # Using 0.0 for delta_percent when baseline is zero (undefined)
        stats = ModelCostStatistics(
            baseline_total=0.0,
            replay_total=50.0,
            delta_total=50.0,
            delta_percent=0.0,  # Undefined when baseline is zero
            baseline_avg_per_execution=0.0,
            replay_avg_per_execution=5.0,
        )

        assert stats.baseline_total == 0.0
        assert stats.replay_total == 50.0
        assert stats.delta_percent == 0.0  # Undefined percent


@pytest.mark.unit
class TestFromCostValues:
    """Test factory method for computing stats from raw values."""

    def test_from_cost_values_computes_totals(self):
        """Total cost is sum of all values."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs = [10.0, 20.0, 30.0]
        replay_costs = [12.0, 22.0, 32.0]

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is not None
        assert stats.baseline_total == 60.0  # 10 + 20 + 30
        assert stats.replay_total == 66.0  # 12 + 22 + 32

    def test_from_cost_values_computes_avg_per_execution(self):
        """Average per execution calculated correctly."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs = [10.0, 20.0, 30.0]  # total=60, avg=20
        replay_costs = [15.0, 25.0, 35.0]  # total=75, avg=25

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is not None
        assert stats.baseline_avg_per_execution == 20.0
        assert stats.replay_avg_per_execution == 25.0

    def test_from_cost_values_computes_deltas(self):
        """Delta values computed correctly from raw costs."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs = [100.0]  # total=100
        replay_costs = [150.0]  # total=150

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is not None
        assert stats.delta_total == 50.0  # 150 - 100
        assert stats.delta_percent == 50.0  # ((150-100)/100) * 100

    def test_from_cost_values_empty_lists(self):
        """Empty cost lists return None (missing data)."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        stats = ModelCostStatistics.from_cost_values([], [])

        assert stats is None

    def test_from_cost_values_mismatched_lengths(self):
        """Different length lists still compute correctly."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs = [10.0, 20.0, 30.0]  # 3 executions, total=60
        replay_costs = [15.0, 25.0]  # 2 executions, total=40

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is not None
        assert stats.baseline_total == 60.0
        assert stats.replay_total == 40.0
        # Averages based on respective execution counts
        assert stats.baseline_avg_per_execution == 20.0  # 60/3
        assert stats.replay_avg_per_execution == 20.0  # 40/2

    def test_from_cost_values_with_none_values(self):
        """None values in list return None (incomplete data)."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs: list[float | None] = [10.0, None, 30.0]
        replay_costs: list[float | None] = [12.0, 22.0, 32.0]

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is None

    def test_from_cost_values_with_none_in_replay(self):
        """None values in replay list return None."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs: list[float | None] = [10.0, 20.0, 30.0]
        replay_costs: list[float | None] = [12.0, None, 32.0]

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is None

    def test_from_cost_values_with_zero_baseline(self):
        """Zero baseline total handled gracefully."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        baseline_costs = [0.0, 0.0]
        replay_costs = [10.0, 20.0]

        stats = ModelCostStatistics.from_cost_values(baseline_costs, replay_costs)

        assert stats is not None
        assert stats.baseline_total == 0.0
        assert stats.replay_total == 30.0
        assert stats.delta_total == 30.0
        # delta_percent should be 0.0 when baseline is zero (undefined)
        assert stats.delta_percent == 0.0


@pytest.mark.unit
class TestSerialization:
    """Test model serialization."""

    def test_model_dump(self):
        """Model can be serialized to dict."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        stats = ModelCostStatistics(
            baseline_total=100.0,
            replay_total=142.0,
            delta_total=42.0,
            delta_percent=42.0,
            baseline_avg_per_execution=10.0,
            replay_avg_per_execution=14.2,
        )

        data = stats.model_dump()

        assert data["baseline_total"] == 100.0
        assert data["replay_total"] == 142.0
        assert data["delta_total"] == 42.0
        assert data["delta_percent"] == 42.0
        assert data["baseline_avg_per_execution"] == 10.0
        assert data["replay_avg_per_execution"] == 14.2

    def test_model_validate_from_dict(self):
        """Model can be created from dict."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        data = {
            "baseline_total": 100.0,
            "replay_total": 142.0,
            "delta_total": 42.0,
            "delta_percent": 42.0,
            "baseline_avg_per_execution": 10.0,
            "replay_avg_per_execution": 14.2,
        }

        stats = ModelCostStatistics.model_validate(data)

        assert stats.baseline_total == 100.0
        assert stats.replay_total == 142.0


@pytest.mark.unit
class TestExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_extra_fields_forbidden(self):
        """Extra fields should raise ValidationError."""
        from omnibase_core.models.evidence.model_cost_statistics import (
            ModelCostStatistics,
        )

        with pytest.raises(ValidationError):
            ModelCostStatistics(
                baseline_total=100.0,
                replay_total=142.0,
                delta_total=42.0,
                delta_percent=42.0,
                baseline_avg_per_execution=10.0,
                replay_avg_per_execution=14.2,
                extra_field="not allowed",  # type: ignore[call-arg]
            )
