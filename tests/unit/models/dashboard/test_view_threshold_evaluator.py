# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the pure view threshold evaluator (OMN-21999, AC2)."""

import math

import jsonschema
import pytest

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold
from omnibase_core.models.dashboard.model_severity_verdict import ModelSeverityVerdict
from omnibase_core.models.dashboard.model_view_threshold_band import (
    ModelViewThresholdBand,
)
from omnibase_core.models.dashboard.model_view_threshold_out_of_band import (
    ModelViewThresholdOutOfBand,
)
from omnibase_core.models.dashboard.model_view_threshold_policy import (
    ModelViewThresholdPolicy,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_view_threshold_evaluator import evaluate_view_threshold


def band(
    lower: float,
    upper: float | None,
    severity: EnumStatusSeverity,
    color: str,
    label: str | None = None,
) -> ModelViewThresholdBand:
    return ModelViewThresholdBand(
        threshold=ModelMetricThreshold(value=lower, color=color, label=label),
        upper_exclusive=upper,
        severity=severity,
    )


# bands: [0, 10) nominal, [10, 60) attention, gap [60, 100), [100, inf) critical
POLICY = ModelViewThresholdPolicy(
    policy_id="consumer-lag",
    policy_version=ModelSemVer(major=2, minor=1, patch=0),
    mapped_field="lag_seconds",
    bands=(
        band(0, 10, EnumStatusSeverity.NOMINAL, "color_status_success", "Fine"),
        band(10, 60, EnumStatusSeverity.ATTENTION, "color_status_warning"),
        band(100, None, EnumStatusSeverity.CRITICAL, "color_status_error", "Stuck"),
    ),
)


@pytest.mark.unit
class TestViewThresholdEvaluator:
    @pytest.mark.parametrize(
        ("value", "severity"),
        [
            (0.0, EnumStatusSeverity.NOMINAL),  # first lower bound is inclusive
            (9.999, EnumStatusSeverity.NOMINAL),
            (
                10.0,
                EnumStatusSeverity.ATTENTION,
            ),  # shared boundary belongs to the upper band
            (59.999, EnumStatusSeverity.ATTENTION),
            (
                100.0,
                EnumStatusSeverity.CRITICAL,
            ),  # lower bound after a gap is inclusive
            (1e12, EnumStatusSeverity.CRITICAL),  # unbounded top band
        ],
    )
    def test_view_threshold_evaluator_returns_declared_band_at_boundaries(
        self, value: float, severity: EnumStatusSeverity
    ) -> None:
        result = evaluate_view_threshold(POLICY, value)
        assert isinstance(result, ModelSeverityVerdict)
        assert result.severity is severity

    def test_view_threshold_evaluator_verdict_carries_policy_identity(self) -> None:
        result = evaluate_view_threshold(POLICY, 5.0)
        assert isinstance(result, ModelSeverityVerdict)
        assert result.policy_id == "consumer-lag"
        assert result.policy_version == ModelSemVer(major=2, minor=1, patch=0)
        assert result.policy_digest == POLICY.compute_digest()

    def test_view_threshold_evaluator_status_value_is_label_else_severity(self) -> None:
        labelled = evaluate_view_threshold(POLICY, 5.0)
        unlabelled = evaluate_view_threshold(POLICY, 30.0)
        assert isinstance(labelled, ModelSeverityVerdict)
        assert isinstance(unlabelled, ModelSeverityVerdict)
        assert labelled.status_value == "Fine"
        assert unlabelled.status_value == "attention"

    @pytest.mark.parametrize("value", [-0.001, -1e9, 60.0, 99.999])
    def test_view_threshold_evaluator_value_in_no_band_is_out_of_band(
        self, value: float
    ) -> None:
        result = evaluate_view_threshold(POLICY, value)
        assert isinstance(result, ModelViewThresholdOutOfBand)
        assert result.value == value
        assert result.policy_id == "consumer-lag"
        assert result.policy_version == ModelSemVer(major=2, minor=1, patch=0)
        assert result.policy_digest == POLICY.compute_digest()
        assert result.mapped_field == "lag_seconds"

    def test_view_threshold_evaluator_above_last_bounded_band_is_out_of_band(
        self,
    ) -> None:
        bounded = ModelViewThresholdPolicy(
            policy_id="bounded",
            policy_version=ModelSemVer(major=1, minor=0, patch=0),
            mapped_field="x",
            bands=(band(0, 10, EnumStatusSeverity.NOMINAL, "color_status_success"),),
        )
        assert isinstance(
            evaluate_view_threshold(bounded, 10.0), ModelViewThresholdOutOfBand
        )
        assert isinstance(evaluate_view_threshold(bounded, 9.0), ModelSeverityVerdict)

    def test_view_threshold_evaluator_nan_is_out_of_band_never_a_band(self) -> None:
        result = evaluate_view_threshold(POLICY, math.nan)
        assert isinstance(result, ModelViewThresholdOutOfBand)

    def test_view_threshold_evaluator_infinity_follows_declared_bounds(self) -> None:
        assert isinstance(
            evaluate_view_threshold(POLICY, math.inf), ModelSeverityVerdict
        )
        assert isinstance(
            evaluate_view_threshold(POLICY, -math.inf), ModelViewThresholdOutOfBand
        )

    def test_view_threshold_evaluator_is_pure_and_repeatable(self) -> None:
        before = POLICY.model_dump(mode="json")
        first = evaluate_view_threshold(POLICY, 42.0)
        second = evaluate_view_threshold(POLICY, 42.0)
        assert first == second
        assert POLICY.model_dump(mode="json") == before

    def test_view_threshold_evaluator_out_of_band_validates_against_json_schema(
        self,
    ) -> None:
        result = evaluate_view_threshold(POLICY, 75.0)
        assert isinstance(result, ModelViewThresholdOutOfBand)
        jsonschema.validate(
            result.model_dump(mode="json"),
            ModelViewThresholdOutOfBand.model_json_schema(),
        )
