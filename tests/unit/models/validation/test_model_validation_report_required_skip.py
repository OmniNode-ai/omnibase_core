# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A required validator that was skipped or missing aggregates to non-pass (OMN-21562)."""

from __future__ import annotations

from typing import Any

import pytest

from omnibase_core.enums.enum_validation_status import EnumValidationStatus
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

_DEFAULT = ModelValidationRequestRef(profile="default")


def _finding(validator_id: str, severity: Any) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id=validator_id,
        severity=severity,
        message=f"{validator_id} {severity}",
    )


@pytest.mark.unit
@pytest.mark.parametrize("severity", ["SKIP", "NOT_APPLICABLE", "MISSING"])
def test_required_skip_is_not_pass(severity: str) -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("a", "PASS"), _finding("b", severity)),
        request=_DEFAULT,
        required_validators=("a", "b"),
    )
    assert report.overall_status == "FAIL"


@pytest.mark.unit
@pytest.mark.parametrize("severity", ["SKIP", "NOT_APPLICABLE"])
def test_required_skip_non_required_still_passes(severity: str) -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("a", "PASS"), _finding("b", severity)),
        request=_DEFAULT,
        required_validators=("a",),
    )
    assert report.overall_status == "PASS"


@pytest.mark.unit
def test_required_skip_default_has_no_required_validators() -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("b", "SKIP"),), request=_DEFAULT
    )
    assert report.overall_status == "PASS"
    assert report.required_validators == ()


@pytest.mark.unit
def test_required_skip_advisory_profile_caps_at_warn() -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("b", "SKIP"),),
        request=ModelValidationRequestRef(profile="advisory"),
        required_validators=("b",),
    )
    assert report.overall_status == "WARN"


@pytest.mark.unit
def test_required_skip_inconsistent_status_rejected() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        ModelValidationReport(
            profile="default",
            overall_status="PASS",
            findings=(_finding("b", "SKIP"),),
            required_validators=("b",),
        )


@pytest.mark.unit
def test_required_skip_advisory_severity_does_not_gate() -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("a", "ADVISORY"),),
        request=_DEFAULT,
        required_validators=("a",),
    )
    assert report.overall_status == "PASS"
    assert report.metrics.advisory_count == 1


@pytest.mark.unit
def test_required_skip_missing_and_advisory_json_round_trip() -> None:
    report = ModelValidationReport.from_findings(
        findings=(_finding("a", "MISSING"), _finding("b", "ADVISORY")),
        request=_DEFAULT,
        required_validators=("a",),
    )
    restored = ModelValidationReport.model_validate_json(report.model_dump_json())
    assert restored == report
    assert restored.metrics.missing_count == 1
    assert restored.metrics.advisory_count == 1
    assert {f.severity for f in restored.findings} == {"MISSING", "ADVISORY"}


@pytest.mark.unit
def test_required_skip_enum_members() -> None:
    assert EnumValidationStatus("missing") is EnumValidationStatus.MISSING
    assert EnumValidationStatus("advisory") is EnumValidationStatus.ADVISORY
