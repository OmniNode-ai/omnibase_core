# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelViewThresholdPolicy and its band (OMN-21999, AC1)."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold
from omnibase_core.models.dashboard.model_view_threshold_band import (
    ModelViewThresholdBand,
)
from omnibase_core.models.dashboard.model_view_threshold_policy import (
    ModelViewThresholdPolicy,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def make_band(
    lower: float,
    upper: float | None,
    severity: EnumStatusSeverity,
    color: str = "color_status_success",
    label: str | None = None,
) -> ModelViewThresholdBand:
    return ModelViewThresholdBand(
        threshold=ModelMetricThreshold(value=lower, color=color, label=label),
        upper_exclusive=upper,
        severity=severity,
    )


def make_policy(
    bands: tuple[ModelViewThresholdBand, ...],
) -> ModelViewThresholdPolicy:
    return ModelViewThresholdPolicy(
        policy_id="consumer-lag",
        policy_version=ModelSemVer(major=1, minor=0, patch=0),
        mapped_field="lag_seconds",
        bands=bands,
    )


@pytest.mark.unit
class TestViewThresholdPolicy:
    def test_view_threshold_policy_carries_id_version_field_and_bands(self) -> None:
        policy = make_policy(
            (
                make_band(0, 10, EnumStatusSeverity.NOMINAL),
                make_band(10, 60, EnumStatusSeverity.ATTENTION, "color_status_warning"),
                make_band(60, None, EnumStatusSeverity.CRITICAL, "color_status_error"),
            )
        )
        assert policy.policy_id == "consumer-lag"
        assert policy.policy_version == ModelSemVer(major=1, minor=0, patch=0)
        assert policy.mapped_field == "lag_seconds"
        assert [b.severity for b in policy.bands] == [
            EnumStatusSeverity.NOMINAL,
            EnumStatusSeverity.ATTENTION,
            EnumStatusSeverity.CRITICAL,
        ]

    def test_view_threshold_policy_band_reuses_metric_threshold(self) -> None:
        band = make_band(5, 10, EnumStatusSeverity.NOMINAL)
        assert isinstance(band.threshold, ModelMetricThreshold)

    def test_view_threshold_policy_accepts_gap_between_bands(self) -> None:
        policy = make_policy(
            (
                make_band(0, 10, EnumStatusSeverity.NOMINAL),
                make_band(20, 30, EnumStatusSeverity.ATTENTION),
            )
        )
        assert len(policy.bands) == 2

    def test_view_threshold_policy_refuses_unordered_bands(self) -> None:
        with pytest.raises(ValidationError, match="ascending"):
            make_policy(
                (
                    make_band(20, 30, EnumStatusSeverity.ATTENTION),
                    make_band(0, 10, EnumStatusSeverity.NOMINAL),
                )
            )

    def test_view_threshold_policy_refuses_equal_lower_bounds(self) -> None:
        with pytest.raises(ValidationError, match="ascending"):
            make_policy(
                (
                    make_band(0, 10, EnumStatusSeverity.NOMINAL),
                    make_band(0, 5, EnumStatusSeverity.ATTENTION),
                )
            )

    def test_view_threshold_policy_refuses_overlapping_bands(self) -> None:
        with pytest.raises(ValidationError, match="overlap"):
            make_policy(
                (
                    make_band(0, 15, EnumStatusSeverity.NOMINAL),
                    make_band(10, 30, EnumStatusSeverity.ATTENTION),
                )
            )

    def test_view_threshold_policy_refuses_unbounded_band_before_another(self) -> None:
        with pytest.raises(ValidationError, match="overlap"):
            make_policy(
                (
                    make_band(0, None, EnumStatusSeverity.NOMINAL),
                    make_band(10, 30, EnumStatusSeverity.ATTENTION),
                )
            )

    def test_view_threshold_policy_refuses_empty_band_extent(self) -> None:
        with pytest.raises(ValidationError, match="upper_exclusive"):
            make_band(10, 10, EnumStatusSeverity.NOMINAL)
        with pytest.raises(ValidationError, match="upper_exclusive"):
            make_band(10, 5, EnumStatusSeverity.NOMINAL)

    def test_view_threshold_policy_refuses_no_bands(self) -> None:
        with pytest.raises(ValidationError):
            make_policy(())

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_view_threshold_policy_refuses_non_finite_bounds(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            make_band(bad, 10, EnumStatusSeverity.NOMINAL)
        with pytest.raises(ValidationError):
            make_band(0, bad, EnumStatusSeverity.NOMINAL)

    @pytest.mark.parametrize("bad_id", ["", " ", "has space", "-lead", "a" * 129])
    def test_view_threshold_policy_refuses_malformed_policy_id(
        self, bad_id: str
    ) -> None:
        with pytest.raises(ValidationError):
            ModelViewThresholdPolicy(
                policy_id=bad_id,
                policy_version=ModelSemVer(major=1, minor=0, patch=0),
                mapped_field="lag_seconds",
                bands=(make_band(0, 10, EnumStatusSeverity.NOMINAL),),
            )

    def test_view_threshold_policy_refuses_malformed_mapped_field(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewThresholdPolicy(
                policy_id="consumer-lag",
                policy_version=ModelSemVer(major=1, minor=0, patch=0),
                mapped_field="",
                bands=(make_band(0, 10, EnumStatusSeverity.NOMINAL),),
            )

    def test_view_threshold_policy_is_frozen_and_forbids_extra(self) -> None:
        policy = make_policy((make_band(0, 10, EnumStatusSeverity.NOMINAL),))
        with pytest.raises(ValidationError):
            policy.__setattr__("policy_id", "other")
        with pytest.raises(ValidationError):
            ModelViewThresholdPolicy.model_validate(
                {**policy.model_dump(mode="json"), "default_band": "nominal"}
            )

    def test_view_threshold_policy_has_no_default_band_field(self) -> None:
        assert not any(
            "default" in name for name in ModelViewThresholdPolicy.model_fields
        )

    def test_view_threshold_policy_roundtrips_through_json_schema(self) -> None:
        import jsonschema

        policy = make_policy(
            (
                make_band(0, 10, EnumStatusSeverity.NOMINAL, label="Fine"),
                make_band(10, None, EnumStatusSeverity.CRITICAL, "color_status_error"),
            )
        )
        schema = ModelViewThresholdPolicy.model_json_schema()
        payload = policy.model_dump(mode="json")
        jsonschema.validate(payload, schema)
        assert ModelViewThresholdPolicy.model_validate(payload) == policy
