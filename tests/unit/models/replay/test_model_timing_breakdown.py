"""Tests for ModelTimingBreakdown model.

Tests the timing breakdown model used to represent execution timing comparisons
between baseline and replay runs, with validation of delta consistency.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import ModelTimingBreakdown
from omnibase_core.models.replay.model_phase_time import ModelPhaseTime


@pytest.mark.unit
class TestModelTimingBreakdownCreation:
    """Test ModelTimingBreakdown creation and initialization."""

    def test_creation_with_consistent_values_succeeds(self) -> None:
        """Model can be created with mathematically consistent delta values."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        assert breakdown.baseline_total_ms == 100.0
        assert breakdown.replay_total_ms == 150.0
        assert breakdown.delta_ms == 50.0
        assert breakdown.delta_percent == 50.0

    def test_creation_with_negative_delta_succeeds(self) -> None:
        """Model can be created with negative delta (replay faster than baseline)."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=200.0,
            replay_total_ms=150.0,
            delta_ms=-50.0,
            delta_percent=-25.0,
        )
        assert breakdown.delta_ms == -50.0
        assert breakdown.delta_percent == -25.0

    def test_creation_with_zero_delta_succeeds(self) -> None:
        """Model can be created with zero delta (identical timing)."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=100.0,
            delta_ms=0.0,
            delta_percent=0.0,
        )
        assert breakdown.delta_ms == 0.0
        assert breakdown.delta_percent == 0.0

    def test_creation_with_phases_succeeds(self) -> None:
        """Model can be created with optional phase breakdown."""
        phases = [
            ModelPhaseTime(
                phase_name="init",
                baseline_ms=10.0,
                replay_ms=15.0,
                delta_percent=50.0,
            ),
            ModelPhaseTime(
                phase_name="execute",
                baseline_ms=90.0,
                replay_ms=135.0,
                delta_percent=50.0,
            ),
        ]
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
            phases=phases,
        )
        assert breakdown.phases is not None
        assert len(breakdown.phases) == 2
        assert breakdown.phases[0].phase_name == "init"

    def test_creation_with_none_phases_succeeds(self) -> None:
        """Model can be created without phase breakdown (phases=None)."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
            phases=None,
        )
        assert breakdown.phases is None


@pytest.mark.unit
class TestModelTimingBreakdownDeltaValidation:
    """Test delta_ms and delta_percent validation."""

    def test_validation_fails_when_delta_ms_inconsistent(self) -> None:
        """Validation fails if delta_ms does not match replay - baseline."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=150.0,
                delta_ms=-10.0,  # Should be +50.0
                delta_percent=50.0,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "delta_ms" in str(errors[0]["msg"])
        assert "inconsistent" in str(errors[0]["msg"]).lower()

    def test_validation_fails_when_delta_percent_inconsistent(self) -> None:
        """Validation fails if delta_percent does not match calculation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=150.0,
                delta_ms=50.0,
                delta_percent=-10.0,  # Should be +50.0
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "delta_percent" in str(errors[0]["msg"])
        assert "inconsistent" in str(errors[0]["msg"]).lower()

    def test_validation_allows_small_floating_point_differences(self) -> None:
        """Validation allows small floating-point precision differences."""
        # 0.005 difference is within tolerance (0.01)
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.005,
            delta_percent=50.005,
        )
        assert breakdown.delta_ms == 50.005
        assert breakdown.delta_percent == 50.005

    def test_validation_rejects_beyond_tolerance_delta_ms(self) -> None:
        """Validation rejects delta_ms differences beyond tolerance."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=150.0,
                delta_ms=50.02,  # 0.02 difference > 0.01 tolerance
                delta_percent=50.02,
            )
        errors = exc_info.value.errors()
        assert "delta_ms" in str(errors[0]["msg"])

    def test_validation_rejects_beyond_tolerance_delta_percent(self) -> None:
        """Validation rejects delta_percent differences beyond tolerance."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=150.0,
                delta_ms=50.0,
                delta_percent=50.02,  # 0.02 difference > 0.01 tolerance
            )
        errors = exc_info.value.errors()
        assert "delta_percent" in str(errors[0]["msg"])


@pytest.mark.unit
class TestModelTimingBreakdownZeroBaselineEdgeCase:
    """Test edge cases when baseline_total_ms is zero."""

    def test_zero_baseline_skips_delta_percent_validation(self) -> None:
        """When baseline is zero, delta_percent validation is skipped."""
        # Percentage change from zero is mathematically undefined
        # So we skip delta_percent validation, allowing any value
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=0.0,
            replay_total_ms=100.0,
            delta_ms=100.0,  # Still validated: 100 - 0 = 100
            delta_percent=999.0,  # Any value allowed when baseline is 0
        )
        assert breakdown.baseline_total_ms == 0.0
        assert breakdown.delta_percent == 999.0

    def test_zero_baseline_still_validates_delta_ms(self) -> None:
        """When baseline is zero, delta_ms is still validated."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=0.0,
                replay_total_ms=100.0,
                delta_ms=50.0,  # Should be 100.0
                delta_percent=0.0,
            )
        errors = exc_info.value.errors()
        assert "delta_ms" in str(errors[0]["msg"])

    def test_zero_baseline_zero_replay_allows_zero_delta(self) -> None:
        """When both baseline and replay are zero, delta should be zero."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=0.0,
            replay_total_ms=0.0,
            delta_ms=0.0,
            delta_percent=0.0,  # Any value allowed, but 0 is reasonable
        )
        assert breakdown.delta_ms == 0.0

    def test_zero_baseline_allows_negative_delta_percent(self) -> None:
        """When baseline is zero, even negative delta_percent is allowed."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=0.0,
            replay_total_ms=50.0,
            delta_ms=50.0,
            delta_percent=-100.0,  # Any value allowed
        )
        assert breakdown.delta_percent == -100.0


@pytest.mark.unit
class TestModelTimingBreakdownFieldValidation:
    """Test field-level validation constraints."""

    def test_validation_fails_when_baseline_negative(self) -> None:
        """Validation fails if baseline_total_ms is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=-10.0,
                replay_total_ms=100.0,
                delta_ms=110.0,
                delta_percent=0.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("baseline_total_ms",) for e in errors)

    def test_validation_fails_when_replay_negative(self) -> None:
        """Validation fails if replay_total_ms is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=-10.0,
                delta_ms=-110.0,
                delta_percent=-110.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("replay_total_ms",) for e in errors)


@pytest.mark.unit
class TestModelTimingBreakdownImmutability:
    """Test immutability of ModelTimingBreakdown model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        with pytest.raises(ValidationError):
            breakdown.baseline_total_ms = 200.0  # type: ignore[misc]
        with pytest.raises(ValidationError):
            breakdown.delta_ms = 0.0  # type: ignore[misc]

    def test_hashing_frozen_model_succeeds(self) -> None:
        """Hashing frozen model succeeds for use in sets and dict keys."""
        breakdown1 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        breakdown2 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        breakdown_set = {breakdown1, breakdown2}
        assert len(breakdown_set) == 1


@pytest.mark.unit
class TestModelTimingBreakdownSerialization:
    """Test serialization of ModelTimingBreakdown model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        data = breakdown.model_dump()
        assert isinstance(data, dict)
        assert data["baseline_total_ms"] == 100.0
        assert data["replay_total_ms"] == 150.0
        assert data["delta_ms"] == 50.0
        assert data["delta_percent"] == 50.0
        assert data["phases"] is None

    def test_serialization_to_json_succeeds(self) -> None:
        """Serialization to JSON returns valid string representation."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        json_str = breakdown.model_dump_json()
        assert isinstance(json_str, str)
        assert '"baseline_total_ms":100.0' in json_str
        assert '"delta_ms":50.0' in json_str

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data = {
            "baseline_total_ms": 100.0,
            "replay_total_ms": 150.0,
            "delta_ms": 50.0,
            "delta_percent": 50.0,
        }
        breakdown = ModelTimingBreakdown(**data)
        assert breakdown.baseline_total_ms == 100.0
        assert breakdown.delta_percent == 50.0

    def test_model_validate_from_attributes_succeeds(self) -> None:
        """Model validation from object attributes creates valid model."""

        class TimingData:
            """Mock object with timing attributes."""

            def __init__(self) -> None:
                self.baseline_total_ms = 100.0
                self.replay_total_ms = 150.0
                self.delta_ms = 50.0
                self.delta_percent = 50.0
                self.phases = None

        breakdown = ModelTimingBreakdown.model_validate(TimingData())
        assert breakdown.baseline_total_ms == 100.0
        assert breakdown.delta_percent == 50.0


@pytest.mark.unit
class TestModelTimingBreakdownEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_creation_with_very_small_values_succeeds(self) -> None:
        """Creation with very small timing values succeeds."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=0.001,
            replay_total_ms=0.002,
            delta_ms=0.001,
            delta_percent=100.0,
        )
        assert breakdown.baseline_total_ms == 0.001

    def test_creation_with_very_large_values_succeeds(self) -> None:
        """Creation with very large timing values succeeds."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=1000000.0,
            replay_total_ms=1500000.0,
            delta_ms=500000.0,
            delta_percent=50.0,
        )
        assert breakdown.baseline_total_ms == 1000000.0

    def test_creation_with_fractional_values_succeeds(self) -> None:
        """Creation with fractional timing values succeeds."""
        breakdown = ModelTimingBreakdown(
            baseline_total_ms=33.333,
            replay_total_ms=66.666,
            delta_ms=33.333,
            delta_percent=99.999,  # (33.333/33.333)*100 ≈ 100, close enough
        )
        # This should pass within tolerance
        assert abs(breakdown.delta_percent - 100.0) < 1.0

    def test_validation_fails_with_extra_fields(self) -> None:
        """Validation fails with extra fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTimingBreakdown(
                baseline_total_ms=100.0,
                replay_total_ms=150.0,
                delta_ms=50.0,
                delta_percent=50.0,
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)


@pytest.mark.unit
class TestModelTimingBreakdownEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        breakdown1 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        breakdown2 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        assert breakdown1 == breakdown2

    def test_equality_when_different_delta_returns_false(self) -> None:
        """Two instances with different delta values are not equal."""
        breakdown1 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=150.0,
            delta_ms=50.0,
            delta_percent=50.0,
        )
        breakdown2 = ModelTimingBreakdown(
            baseline_total_ms=100.0,
            replay_total_ms=160.0,
            delta_ms=60.0,
            delta_percent=60.0,
        )
        assert breakdown1 != breakdown2
