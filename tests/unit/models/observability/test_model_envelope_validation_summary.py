# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEnvelopeValidationSummary."""

import pytest

from omnibase_core.enums.enum_envelope_validation_failure_type import (
    EnumEnvelopeValidationFailureType,
)
from omnibase_core.models.observability.model_envelope_validation_summary import (
    ModelEnvelopeValidationSummary,
)


class TestModelEnvelopeValidationSummaryDefaults:
    """Tests for ModelEnvelopeValidationSummary default state."""

    def test_create_empty_zero_state(self) -> None:
        """create_empty() produces a summary with zero observations."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        assert summary.timing.total_validations == 0
        assert summary.failures.total_validations == 0

    def test_default_alerts_not_elevated(self) -> None:
        """Default summary has no elevated alerts."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        assert not summary.has_elevated_failure_rate
        assert not summary.has_elevated_correlation_id_generation

    def test_created_at_set(self) -> None:
        """created_at is set on a fresh instance."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        assert summary.created_at is not None


class TestModelEnvelopeValidationSummaryRecordValidation:
    """Tests for record_validation() atomic update of sub-models."""

    def test_record_pass_updates_both_submodels(self) -> None:
        """A passing validation updates both timing and failure sub-models."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=1.5,
            passed=True,
        )

        assert summary.timing.total_validations == 1
        assert summary.timing.passed_validations == 1
        assert summary.failures.total_validations == 1
        assert summary.failures.total_failures == 0

    def test_record_failure_updates_both_submodels(self) -> None:
        """A failing validation updates both timing and failure sub-models."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=0.3,
            passed=False,
            failure_type=EnumEnvelopeValidationFailureType.MISSING_CORRELATION_ID,
        )

        assert summary.timing.failed_validations == 1
        assert summary.failures.total_failures == 1
        assert summary.failures.failures_by_type["missing_correlation_id"] == 1

    def test_immutability(self) -> None:
        """record_validation does not mutate the original summary."""
        original = ModelEnvelopeValidationSummary.create_empty()
        _ = original.record_validation(total_duration_ms=1.0, passed=True)
        assert original.timing.total_validations == 0

    def test_step_durations_forwarded(self) -> None:
        """Step duration breakdown is forwarded to the timing sub-model."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=2.0,
            passed=True,
            step_durations_ms={"correlation_id": 0.5, "payload_presence": 0.3},
        )

        assert summary.timing.step_counts["correlation_id"] == 1
        assert summary.timing.step_counts["payload_presence"] == 1

    def test_correlation_id_generated_forwarded(self) -> None:
        """correlation_id_was_generated is forwarded to failure sub-model."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=1.0,
            passed=True,
            correlation_id_was_generated=True,
        )

        assert summary.failures.correlation_ids_generated == 1

    def test_failure_type_defaults_to_unknown(self) -> None:
        """If failure_type is omitted for a failing validation, UNKNOWN is used."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=0.5,
            passed=False,
            # No failure_type provided
        )

        assert summary.failures.failures_by_type["unknown"] == 1

    def test_created_at_preserved_across_updates(self) -> None:
        """created_at on the summary is not changed by record_validation."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        original_ts = summary.created_at
        summary = summary.record_validation(total_duration_ms=1.0, passed=True)
        assert summary.created_at == original_ts


class TestModelEnvelopeValidationSummaryAlerting:
    """Tests for alert delegation to sub-models."""

    def test_elevated_failure_rate_alert(self) -> None:
        """has_elevated_failure_rate reflects failure sub-model alert."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        for _ in range(4):
            summary = summary.record_validation(total_duration_ms=1.0, passed=True)
        summary = summary.record_validation(
            total_duration_ms=0.5,
            passed=False,
            failure_type=EnumEnvelopeValidationFailureType.EMPTY_PAYLOAD,
        )
        # 20% failure rate — above default 5% threshold
        assert summary.has_elevated_failure_rate

    def test_elevated_correlation_id_generation_alert(self) -> None:
        """has_elevated_correlation_id_generation reflects failure sub-model alert."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        for _ in range(5):
            summary = summary.record_validation(
                total_duration_ms=1.0,
                passed=True,
                correlation_id_was_generated=True,
            )
        for _ in range(5):
            summary = summary.record_validation(
                total_duration_ms=1.0,
                passed=True,
                correlation_id_was_generated=False,
            )
        # 50% generation ratio — above default 20% threshold
        assert summary.has_elevated_correlation_id_generation


class TestModelEnvelopeValidationSummaryToDict:
    """Tests for to_dict() output structure."""

    def test_to_dict_top_level_keys(self) -> None:
        """to_dict() returns timing, failures, alerts, and created_at."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        result = summary.to_dict()
        assert set(result.keys()) == {"timing", "failures", "alerts", "created_at"}

    def test_to_dict_alerts_keys(self) -> None:
        """to_dict() alerts section has the expected keys."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        alerts = summary.to_dict()["alerts"]
        assert isinstance(alerts, dict)
        assert set(alerts.keys()) == {  # type: ignore[union-attr]
            "elevated_failure_rate",
            "elevated_correlation_id_generation",
        }

    def test_to_dict_timing_has_percentiles(self) -> None:
        """to_dict() timing section includes p50/p95/p99 fields."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        timing = summary.to_dict()["timing"]
        assert isinstance(timing, dict)
        assert "p50_duration_ms" in timing  # type: ignore[operator]
        assert "p95_duration_ms" in timing  # type: ignore[operator]
        assert "p99_duration_ms" in timing  # type: ignore[operator]


class TestModelEnvelopeValidationSummaryEnumIntegration:
    """Tests for EnumEnvelopeValidationFailureType integration."""

    @pytest.mark.parametrize(
        "failure_type",
        list(EnumEnvelopeValidationFailureType),
    )
    def test_all_failure_types_can_be_recorded(
        self, failure_type: EnumEnvelopeValidationFailureType
    ) -> None:
        """All EnumEnvelopeValidationFailureType members can be recorded."""
        summary = ModelEnvelopeValidationSummary.create_empty()
        summary = summary.record_validation(
            total_duration_ms=0.5,
            passed=False,
            failure_type=failure_type,
        )
        assert summary.failures.failures_by_type[failure_type.value] == 1
