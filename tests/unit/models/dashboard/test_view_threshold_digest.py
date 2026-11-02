# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the view threshold policy digest and pin check (OMN-21999, AC3)."""

from collections.abc import Callable

import jsonschema
import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold
from omnibase_core.models.dashboard.model_view_threshold_band import (
    ModelViewThresholdBand,
)
from omnibase_core.models.dashboard.model_view_threshold_policy import (
    ModelViewThresholdPolicy,
)
from omnibase_core.models.dashboard.model_view_threshold_policy_pin import (
    ModelViewThresholdPolicyPin,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

VERSION = ModelSemVer(major=1, minor=0, patch=0)


def band(
    lower: float,
    upper: float | None,
    severity: EnumStatusSeverity = EnumStatusSeverity.NOMINAL,
    color: str = "color_status_success",
    label: str | None = None,
) -> ModelViewThresholdBand:
    return ModelViewThresholdBand(
        threshold=ModelMetricThreshold(value=lower, color=color, label=label),
        upper_exclusive=upper,
        severity=severity,
    )


def policy(*bands: ModelViewThresholdBand) -> ModelViewThresholdPolicy:
    return ModelViewThresholdPolicy(
        policy_id="consumer-lag",
        policy_version=VERSION,
        mapped_field="lag_seconds",
        bands=bands,
    )


def base_bands() -> tuple[ModelViewThresholdBand, ...]:
    return (
        band(0, 10, label="Fine"),
        band(10, 60, EnumStatusSeverity.ATTENTION, "color_status_warning"),
    )


def pin_for(p: ModelViewThresholdPolicy) -> ModelViewThresholdPolicyPin:
    return ModelViewThresholdPolicyPin(
        policy_id=p.policy_id,
        policy_version=p.policy_version,
        policy_digest=p.compute_digest(),
    )


# Each variant changes exactly one thing about the base policy's bands.
BAND_CHANGES: dict[str, Callable[[], tuple[ModelViewThresholdBand, ...]]] = {
    "lower_bound": lambda: (band(1, 10, label="Fine"), base_bands()[1]),
    "upper_bound": lambda: (
        band(0, 11, label="Fine"),
        band(11, 60, EnumStatusSeverity.ATTENTION, "color_status_warning"),
    ),
    "severity": lambda: (
        band(0, 10, EnumStatusSeverity.UNKNOWN, label="Fine"),
        base_bands()[1],
    ),
    "colour_token": lambda: (
        band(0, 10, color="color_status_error", label="Fine"),
        base_bands()[1],
    ),
    "label": lambda: (band(0, 10, label="Fin"), base_bands()[1]),
    "label_removed": lambda: (band(0, 10), base_bands()[1]),
    "band_added": lambda: (
        *base_bands(),
        band(60, None, EnumStatusSeverity.CRITICAL, "color_status_error"),
    ),
    "band_removed": lambda: (base_bands()[0],),
    "unbounded_top": lambda: (
        base_bands()[0],
        band(10, None, EnumStatusSeverity.ATTENTION, "color_status_warning"),
    ),
}


@pytest.mark.unit
class TestViewThresholdDigest:
    def test_view_threshold_digest_is_sha256_prefixed_and_deterministic(self) -> None:
        digest = policy(*base_bands()).compute_digest()
        assert digest.startswith("sha256:")
        assert len(digest) == len("sha256:") + 64
        assert digest == policy(*base_bands()).compute_digest()

    @pytest.mark.parametrize("change", sorted(BAND_CHANGES))
    def test_view_threshold_digest_changes_when_any_band_changes(
        self, change: str
    ) -> None:
        original = policy(*base_bands())
        changed = policy(*BAND_CHANGES[change]())
        assert changed.compute_digest() != original.compute_digest()

    def test_view_threshold_digest_changes_with_id_version_and_field(self) -> None:
        original = policy(*base_bands())
        for update in (
            {"policy_id": "other"},
            {"policy_version": ModelSemVer(major=1, minor=0, patch=1)},
            {"mapped_field": "other_field"},
        ):
            assert (
                original.model_copy(update=update).compute_digest()
                != original.compute_digest()
            )

    def test_view_threshold_digest_pin_accepts_matching_reference(self) -> None:
        p = policy(*base_bands())
        p.verify_pin(pin_for(p))

    def test_view_threshold_digest_pin_refuses_changed_band(self) -> None:
        pinned = pin_for(policy(*base_bands()))
        changed = policy(*BAND_CHANGES["upper_bound"]())
        with pytest.raises(ModelOnexError) as exc_info:
            changed.verify_pin(pinned)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "digest" in exc_info.value.message

    def test_view_threshold_digest_pin_refuses_other_id_or_version(self) -> None:
        p = policy(*base_bands())
        good = pin_for(p)
        with pytest.raises(ModelOnexError, match="policy_id"):
            p.verify_pin(good.model_copy(update={"policy_id": "other"}))
        with pytest.raises(ModelOnexError, match="policy_version"):
            p.verify_pin(
                good.model_copy(
                    update={"policy_version": ModelSemVer(major=9, minor=0, patch=0)}
                )
            )

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "abc",
            "sha256:ABC",
            "sha256:" + "g" * 64,
            "sha256:" + "a" * 63,
            "md5:" + "a" * 32,
        ],
    )
    def test_view_threshold_digest_pin_refuses_malformed_digest(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            ModelViewThresholdPolicyPin(
                policy_id="consumer-lag", policy_version=VERSION, policy_digest=bad
            )

    def test_view_threshold_digest_pin_is_frozen_extra_forbid_and_schema_valid(
        self,
    ) -> None:
        pin = pin_for(policy(*base_bands()))
        payload = pin.model_dump(mode="json")
        jsonschema.validate(payload, ModelViewThresholdPolicyPin.model_json_schema())
        with pytest.raises(ValidationError):
            ModelViewThresholdPolicyPin.model_validate({**payload, "extra": 1})
        with pytest.raises(ValidationError):
            pin.__setattr__("policy_id", "x")
