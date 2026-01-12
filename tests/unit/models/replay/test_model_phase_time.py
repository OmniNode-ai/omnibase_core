"""Tests for ModelPhaseTime model.

Tests the phase timing model used to represent individual execution phase
timings between baseline and replay runs, with validation of timing constraints
and delta_percent consistency.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import ModelTimingBreakdown
from omnibase_core.models.replay.model_phase_time import ModelPhaseTime


@pytest.mark.unit
class TestModelPhaseTimeCreation:
    """Test ModelPhaseTime creation and initialization."""

    def test_creation_with_valid_values_succeeds(self) -> None:
        """Model can be created with mathematically consistent values."""
        # baseline=100, replay=120, delta=20%
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        assert phase.phase_name == "compute"
        assert phase.baseline_ms == 100.0
        assert phase.replay_ms == 120.0
        assert phase.delta_percent == 20.0

    def test_creation_with_zero_baseline_succeeds(self) -> None:
        """Model can be created with zero baseline (edge case)."""
        # When baseline is zero, delta_percent validation is skipped
        phase = ModelPhaseTime(
            phase_name="init",
            baseline_ms=0.0,
            replay_ms=50.0,
            delta_percent=999.0,  # Any value allowed when baseline is 0
        )
        assert phase.baseline_ms == 0.0
        assert phase.replay_ms == 50.0
        assert phase.delta_percent == 999.0

    def test_creation_with_negative_delta_succeeds(self) -> None:
        """Model can be created with negative delta (replay faster than baseline)."""
        # baseline=200, replay=150, delta=-25%
        phase = ModelPhaseTime(
            phase_name="execute",
            baseline_ms=200.0,
            replay_ms=150.0,
            delta_percent=-25.0,
        )
        assert phase.delta_percent == -25.0

    def test_creation_with_zero_delta_succeeds(self) -> None:
        """Model can be created with zero delta (identical timing)."""
        phase = ModelPhaseTime(
            phase_name="finalize",
            baseline_ms=100.0,
            replay_ms=100.0,
            delta_percent=0.0,
        )
        assert phase.delta_percent == 0.0


@pytest.mark.unit
class TestModelPhaseTimeValidation:
    """Test field-level validation constraints."""

    def test_validation_fails_when_baseline_ms_is_negative(self) -> None:
        """Validation fails if baseline_ms is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=-1.0,
                replay_ms=100.0,
                delta_percent=0.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("baseline_ms",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_replay_ms_is_negative(self) -> None:
        """Validation fails if replay_ms is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=100.0,
                replay_ms=-1.0,
                delta_percent=0.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("replay_ms",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_phase_name_is_empty(self) -> None:
        """Validation fails if phase_name is empty string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="",
                baseline_ms=100.0,
                replay_ms=120.0,
                delta_percent=20.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("phase_name",) for e in errors)

    def test_validation_fails_when_delta_percent_is_inconsistent(self) -> None:
        """Validation fails if delta_percent does not match calculation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=100.0,
                replay_ms=120.0,
                delta_percent=-10.0,  # Should be +20.0
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "delta_percent" in str(errors[0]["msg"])
        assert "inconsistent" in str(errors[0]["msg"]).lower()


@pytest.mark.unit
class TestModelPhaseTimeZeroBaselineEdgeCases:
    """Test edge cases when baseline_ms is zero."""

    def test_validation_succeeds_when_baseline_is_zero(self) -> None:
        """When baseline is zero, delta_percent validation is skipped."""
        # Percentage change from zero is mathematically undefined
        # So we skip delta_percent validation, allowing any value
        phase = ModelPhaseTime(
            phase_name="init",
            baseline_ms=0.0,
            replay_ms=100.0,
            delta_percent=999.0,  # Any value allowed when baseline is 0
        )
        assert phase.baseline_ms == 0.0
        assert phase.delta_percent == 999.0

    def test_zero_baseline_allows_negative_delta_percent(self) -> None:
        """When baseline is zero, even negative delta_percent is allowed."""
        phase = ModelPhaseTime(
            phase_name="init",
            baseline_ms=0.0,
            replay_ms=50.0,
            delta_percent=-100.0,  # Any value allowed
        )
        assert phase.delta_percent == -100.0

    def test_zero_baseline_zero_replay_allows_any_delta(self) -> None:
        """When both baseline and replay are zero, any delta is allowed."""
        phase = ModelPhaseTime(
            phase_name="init",
            baseline_ms=0.0,
            replay_ms=0.0,
            delta_percent=0.0,  # 0 is reasonable, but any value is allowed
        )
        assert phase.delta_percent == 0.0


@pytest.mark.unit
class TestModelPhaseTimeDeltaPercentConsistency:
    """Test delta_percent mathematical consistency validation."""

    def test_validation_succeeds_with_correct_delta_percent(self) -> None:
        """Validation passes with mathematically correct delta_percent."""
        # baseline=80, replay=100, delta = (100-80)/80 * 100 = 25%
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=80.0,
            replay_ms=100.0,
            delta_percent=25.0,
        )
        assert phase.delta_percent == 25.0

    def test_validation_allows_small_floating_point_differences(self) -> None:
        """Validation allows small floating-point precision differences."""
        # Expected delta: ((120 - 100) / 100) * 100 = 20.0
        # 0.005 difference is within tolerance (0.01)
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.005,
        )
        assert phase.delta_percent == 20.005

    def test_validation_rejects_beyond_tolerance_delta_percent(self) -> None:
        """Validation rejects delta_percent differences beyond tolerance."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=100.0,
                replay_ms=120.0,
                delta_percent=20.02,  # 0.02 difference > 0.01 tolerance
            )
        errors = exc_info.value.errors()
        assert "delta_percent" in str(errors[0]["msg"])

    def test_validation_with_large_percentage_change(self) -> None:
        """Validation handles large percentage changes correctly."""
        # baseline=10, replay=110, delta = (110-10)/10 * 100 = 1000%
        phase = ModelPhaseTime(
            phase_name="slow_phase",
            baseline_ms=10.0,
            replay_ms=110.0,
            delta_percent=1000.0,
        )
        assert phase.delta_percent == 1000.0

    def test_validation_with_fractional_values(self) -> None:
        """Validation handles fractional timing values correctly."""
        # baseline=33.333, replay=66.666, delta = (66.666-33.333)/33.333 * 100 ~= 100%
        phase = ModelPhaseTime(
            phase_name="precise_phase",
            baseline_ms=33.333,
            replay_ms=66.666,
            delta_percent=100.0,  # (33.333/33.333)*100 ~= 100
        )
        assert abs(phase.delta_percent - 100.0) < 1.0


@pytest.mark.unit
class TestModelPhaseTimeImmutability:
    """Test immutability of ModelPhaseTime model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        with pytest.raises(ValidationError):
            phase.phase_name = "modified"
        with pytest.raises(ValidationError):
            phase.baseline_ms = 200.0
        with pytest.raises(ValidationError):
            phase.replay_ms = 200.0
        with pytest.raises(ValidationError):
            phase.delta_percent = 0.0

    def test_hashing_frozen_model_succeeds(self) -> None:
        """Hashing frozen model succeeds for use in sets and dict keys."""
        phase1 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        phase2 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        phase_set = {phase1, phase2}
        assert len(phase_set) == 1  # Duplicates are removed


@pytest.mark.unit
class TestModelPhaseTimeSerialization:
    """Test serialization of ModelPhaseTime model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict."""
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        data = phase.model_dump()
        assert isinstance(data, dict)
        assert data["phase_name"] == "compute"
        assert data["baseline_ms"] == 100.0
        assert data["replay_ms"] == 120.0
        assert data["delta_percent"] == 20.0
        assert len(data) == 4

    def test_serialization_to_json_succeeds(self) -> None:
        """Serialization to JSON returns valid string representation."""
        phase = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        json_str = phase.model_dump_json()
        assert isinstance(json_str, str)
        assert '"phase_name":"compute"' in json_str
        assert '"baseline_ms":100.0' in json_str
        assert '"replay_ms":120.0' in json_str
        assert '"delta_percent":20.0' in json_str

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data = {
            "phase_name": "execute",
            "baseline_ms": 50.0,
            "replay_ms": 75.0,
            "delta_percent": 50.0,
        }
        phase = ModelPhaseTime(**data)
        assert phase.phase_name == "execute"
        assert phase.baseline_ms == 50.0
        assert phase.replay_ms == 75.0
        assert phase.delta_percent == 50.0

    def test_model_validate_from_attributes_succeeds(self) -> None:
        """Model validation from object attributes creates valid model."""

        class PhaseData:
            """Mock object with phase timing attributes."""

            def __init__(self) -> None:
                self.phase_name = "compute"
                self.baseline_ms = 100.0
                self.replay_ms = 120.0
                self.delta_percent = 20.0

        phase = ModelPhaseTime.model_validate(PhaseData())
        assert phase.phase_name == "compute"
        assert phase.baseline_ms == 100.0
        assert phase.replay_ms == 120.0
        assert phase.delta_percent == 20.0


@pytest.mark.unit
class TestModelPhaseTimeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_creation_with_very_small_values_succeeds(self) -> None:
        """Creation with very small timing values succeeds."""
        # baseline=0.001, replay=0.002, delta = (0.002-0.001)/0.001 * 100 = 100%
        phase = ModelPhaseTime(
            phase_name="micro_phase",
            baseline_ms=0.001,
            replay_ms=0.002,
            delta_percent=100.0,
        )
        assert phase.baseline_ms == 0.001
        assert phase.replay_ms == 0.002

    def test_creation_with_very_large_values_succeeds(self) -> None:
        """Creation with very large timing values succeeds."""
        # baseline=1000000, replay=1500000, delta = 50%
        phase = ModelPhaseTime(
            phase_name="long_running_phase",
            baseline_ms=1000000.0,
            replay_ms=1500000.0,
            delta_percent=50.0,
        )
        assert phase.baseline_ms == 1000000.0
        assert phase.replay_ms == 1500000.0

    def test_creation_with_unicode_phase_name_succeeds(self) -> None:
        """Creation with unicode characters in phase name succeeds."""
        phase = ModelPhaseTime(
            phase_name="phase_initialization",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        assert phase.phase_name == "phase_initialization"

    def test_validation_fails_with_extra_fields(self) -> None:
        """Validation fails with extra fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                phase_name="compute",
                baseline_ms=100.0,
                replay_ms=120.0,
                delta_percent=20.0,
                extra_field="not allowed",
            )
        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)

    def test_validation_fails_when_phase_name_missing(self) -> None:
        """Validation fails if phase_name is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseTime(
                baseline_ms=100.0,
                replay_ms=120.0,
                delta_percent=20.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("phase_name",) for e in errors)


@pytest.mark.unit
class TestModelPhaseTimeEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        phase1 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        phase2 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        assert phase1 == phase2

    def test_equality_when_different_phase_name_returns_false(self) -> None:
        """Two instances with different phase_name are not equal."""
        phase1 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        phase2 = ModelPhaseTime(
            phase_name="execute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        assert phase1 != phase2

    def test_equality_when_different_timing_returns_false(self) -> None:
        """Two instances with different timing values are not equal."""
        phase1 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=120.0,
            delta_percent=20.0,
        )
        phase2 = ModelPhaseTime(
            phase_name="compute",
            baseline_ms=100.0,
            replay_ms=150.0,
            delta_percent=50.0,
        )
        assert phase1 != phase2


@pytest.mark.unit
class TestModelPhaseTimeInTimingBreakdown:
    """Test ModelPhaseTime integration with ModelTimingBreakdown."""

    def test_phase_time_can_be_used_in_timing_breakdown(self) -> None:
        """ModelPhaseTime instances can be used in ModelTimingBreakdown phases."""
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
        assert breakdown.phases[1].phase_name == "execute"
