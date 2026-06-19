# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidationFinding, ValidationReport, and ValidationMetrics.

OMN-2543: canonical ValidationReport semantics (PASS/WARN/FAIL/ERROR/SKIP/
NOT_APPLICABLE + explicit precedence) retained by OMN-13279.

The ValidationRequest and ValidatorDescriptor models were part of the
superseded Generic Validator Node mechanism (OMN-2362) and were removed in
OMN-13279; their tests were removed with them. The canonical report model
carries its own `ModelValidationRequestRef` duck-type, so it does not depend on
the removed request model.

Coverage:
- All severity literals on ValidationFinding
- All profile modes and their effect on ValidationReport
- Status precedence matrix edge cases
- JSON serialisability without custom encoders
"""

from __future__ import annotations

import json

import pytest

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    SEVERITY_PRECEDENCE,
    ModelValidationFindingEmbed,
    ModelValidationFindingRef,
    ModelValidationMetrics,
    ModelValidationReport,
    ModelValidationRequestRef,
    _compute_overall_status,
)

# ---------------------------------------------------------------------------
# ValidationFinding
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationFinding:
    """Tests for the ValidationFinding model."""

    def test_minimal_construction(self) -> None:
        """ValidationFinding can be constructed with validator_id, severity, message."""
        finding = ModelValidationFinding(
            validator_id="test_validator",
            severity="PASS",
            message="All good.",
        )
        assert finding.validator_id == "test_validator"
        assert finding.severity == "PASS"
        assert finding.message == "All good."
        assert finding.location is None
        assert finding.remediation is None
        assert finding.evidence == {}
        assert finding.rule_id is None

    def test_all_severity_literals(self) -> None:
        """All six severity literals are accepted."""
        for severity in ("PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"):
            finding = ModelValidationFinding(
                validator_id="v",
                severity=severity,  # type: ignore[arg-type]
                message="msg",
            )
            assert finding.severity == severity

    def test_invalid_severity_rejected(self) -> None:
        """Invalid severity raises ValidationError."""
        with pytest.raises(Exception):
            ModelValidationFinding(
                validator_id="v",
                severity="CRITICAL",  # type: ignore[arg-type]
                message="msg",
            )

    def test_full_construction(self) -> None:
        """ValidationFinding accepts all optional fields."""
        finding = ModelValidationFinding(
            validator_id="naming_convention",
            severity="FAIL",
            location="src/foo.py:42",
            message="Bad name.",
            remediation="Rename to snake_case.",
            evidence={"actual": "BadName", "expected_pattern": "^[a-z_]+$"},
            rule_id="NC001",
        )
        assert finding.location == "src/foo.py:42"
        assert finding.rule_id == "NC001"
        assert finding.evidence["actual"] == "BadName"

    def test_frozen(self) -> None:
        """ValidationFinding is immutable."""
        finding = ModelValidationFinding(
            validator_id="v", severity="PASS", message="ok"
        )
        with pytest.raises(Exception):
            finding.message = "changed"  # type: ignore[misc]

    def test_json_serialisable(self) -> None:
        """ValidationFinding serialises to JSON without custom encoders."""
        finding = ModelValidationFinding(
            validator_id="v",
            severity="WARN",
            message="warning",
            evidence={"key": "value", "count": 3},
        )
        data = json.loads(finding.model_dump_json())
        assert data["severity"] == "WARN"
        assert data["evidence"]["count"] == 3


# ---------------------------------------------------------------------------
# Precedence matrix (_compute_overall_status)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSeverityPrecedenceMatrix:
    """Tests for the explicit severity precedence matrix."""

    def test_precedence_constants(self) -> None:
        """SEVERITY_PRECEDENCE encodes ERROR > FAIL > WARN > PASS."""
        assert SEVERITY_PRECEDENCE["ERROR"] > SEVERITY_PRECEDENCE["FAIL"]
        assert SEVERITY_PRECEDENCE["FAIL"] > SEVERITY_PRECEDENCE["WARN"]
        assert SEVERITY_PRECEDENCE["WARN"] > SEVERITY_PRECEDENCE["PASS"]

    def test_skip_not_in_precedence(self) -> None:
        """SKIP is not in the precedence matrix (does not contribute)."""
        assert "SKIP" not in SEVERITY_PRECEDENCE

    def test_not_applicable_not_in_precedence(self) -> None:
        """NOT_APPLICABLE is not in the precedence matrix."""
        assert "NOT_APPLICABLE" not in SEVERITY_PRECEDENCE

    def _make_refs(self, *severities: str) -> tuple[ModelValidationFindingRef, ...]:
        return tuple(
            ModelValidationFindingRef(severity=s, validator_id="v")  # type: ignore[arg-type]
            for s in severities
        )

    def test_no_findings_is_pass(self) -> None:
        """Empty findings produce PASS."""
        assert _compute_overall_status((), "default") == "PASS"

    def test_only_pass_findings_is_pass(self) -> None:
        assert (
            _compute_overall_status(self._make_refs("PASS", "PASS"), "default")
            == "PASS"
        )

    def test_warn_finding_default_profile(self) -> None:
        assert _compute_overall_status(self._make_refs("WARN"), "default") == "WARN"

    def test_fail_finding_default_profile(self) -> None:
        assert _compute_overall_status(self._make_refs("FAIL"), "default") == "FAIL"

    def test_error_finding_default_profile(self) -> None:
        assert _compute_overall_status(self._make_refs("ERROR"), "default") == "ERROR"

    def test_error_dominates_fail(self) -> None:
        """ERROR dominates FAIL."""
        assert (
            _compute_overall_status(self._make_refs("FAIL", "ERROR"), "default")
            == "ERROR"
        )

    def test_fail_dominates_warn(self) -> None:
        assert (
            _compute_overall_status(self._make_refs("WARN", "FAIL"), "default")
            == "FAIL"
        )

    def test_warn_dominates_pass(self) -> None:
        assert (
            _compute_overall_status(self._make_refs("PASS", "WARN"), "default")
            == "WARN"
        )

    def test_skip_does_not_influence(self) -> None:
        """SKIP findings are excluded from status computation."""
        assert _compute_overall_status(self._make_refs("SKIP"), "default") == "PASS"

    def test_not_applicable_does_not_influence(self) -> None:
        """NOT_APPLICABLE findings are excluded from status computation."""
        assert (
            _compute_overall_status(self._make_refs("NOT_APPLICABLE"), "default")
            == "PASS"
        )

    def test_skip_alongside_warn(self) -> None:
        """SKIP alongside WARN still produces WARN."""
        assert (
            _compute_overall_status(self._make_refs("SKIP", "WARN"), "default")
            == "WARN"
        )

    # --- strict profile ---

    def test_strict_elevates_warn_to_fail(self) -> None:
        """'strict' profile elevates WARN to FAIL."""
        assert _compute_overall_status(self._make_refs("WARN"), "strict") == "FAIL"

    def test_strict_pass_is_still_pass(self) -> None:
        """'strict' profile does not elevate PASS."""
        assert _compute_overall_status(self._make_refs("PASS"), "strict") == "PASS"

    def test_strict_fail_stays_fail(self) -> None:
        assert _compute_overall_status(self._make_refs("FAIL"), "strict") == "FAIL"

    def test_strict_error_stays_error(self) -> None:
        assert _compute_overall_status(self._make_refs("ERROR"), "strict") == "ERROR"

    def test_strict_warn_and_error_produces_error(self) -> None:
        """Under strict profile, WARN+ERROR still gives ERROR (ERROR dominates)."""
        assert (
            _compute_overall_status(self._make_refs("WARN", "ERROR"), "strict")
            == "ERROR"
        )

    # --- advisory profile ---

    def test_advisory_fail_capped_at_warn(self) -> None:
        """'advisory' profile caps FAIL at WARN."""
        assert _compute_overall_status(self._make_refs("FAIL"), "advisory") == "WARN"

    def test_advisory_error_capped_at_warn(self) -> None:
        """'advisory' profile caps ERROR at WARN."""
        assert _compute_overall_status(self._make_refs("ERROR"), "advisory") == "WARN"

    def test_advisory_warn_stays_warn(self) -> None:
        assert _compute_overall_status(self._make_refs("WARN"), "advisory") == "WARN"

    def test_advisory_pass_stays_pass(self) -> None:
        assert _compute_overall_status(self._make_refs("PASS"), "advisory") == "PASS"

    def test_advisory_no_findings_is_pass(self) -> None:
        assert _compute_overall_status((), "advisory") == "PASS"


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


def _embed(
    validator_id: str,
    severity: str,
    message: str = "msg",
) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id=validator_id,
        severity=severity,  # type: ignore[arg-type]
        message=message,
    )


@pytest.mark.unit
class TestValidationReport:
    """Tests for the ValidationReport model."""

    def test_from_findings_no_findings(self) -> None:
        """Empty findings produces PASS."""
        req = ModelValidationRequestRef(profile="default")
        report = ModelValidationReport.from_findings(findings=(), request=req)
        assert report.overall_status == "PASS"
        assert report.metrics.total == 0

    def test_from_findings_single_fail(self) -> None:
        req = ModelValidationRequestRef(profile="default")
        findings = (_embed("v", "FAIL"),)
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "FAIL"
        assert report.metrics.fail_count == 1
        assert report.metrics.total == 1

    def test_from_findings_strict_elevates_warn(self) -> None:
        """strict profile: WARN finding produces FAIL overall_status."""
        req = ModelValidationRequestRef(profile="strict")
        findings = (_embed("v", "WARN"),)
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "FAIL"

    def test_from_findings_advisory_caps_fail(self) -> None:
        """advisory profile: FAIL finding produces WARN overall_status."""
        req = ModelValidationRequestRef(profile="advisory")
        findings = (_embed("v", "FAIL"),)
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "WARN"

    def test_from_findings_advisory_caps_error(self) -> None:
        """advisory profile: ERROR finding produces WARN overall_status."""
        req = ModelValidationRequestRef(profile="advisory")
        findings = (_embed("v", "ERROR"),)
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "WARN"

    def test_metrics_counts(self) -> None:
        """ValidationMetrics counts all severities correctly."""
        req = ModelValidationRequestRef(profile="default")
        findings = (
            _embed("v", "PASS"),
            _embed("v", "PASS"),
            _embed("v", "WARN"),
            _embed("v", "FAIL"),
            _embed("v", "ERROR"),
            _embed("v", "SKIP"),
            _embed("v", "NOT_APPLICABLE"),
        )
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        m = report.metrics
        assert m.total == 7
        assert m.pass_count == 2
        assert m.warn_count == 1
        assert m.fail_count == 1
        assert m.error_count == 1
        assert m.skip_count == 1
        assert m.not_applicable_count == 1

    def test_skip_does_not_influence_overall_status(self) -> None:
        """SKIP findings don't change overall_status."""
        req = ModelValidationRequestRef(profile="default")
        findings = (_embed("v", "PASS"), _embed("v", "SKIP"))
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "PASS"

    def test_not_applicable_does_not_influence_overall_status(self) -> None:
        req = ModelValidationRequestRef(profile="default")
        findings = (_embed("v", "PASS"), _embed("v", "NOT_APPLICABLE"))
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "PASS"

    def test_report_is_frozen(self) -> None:
        """ValidationReport is immutable."""
        req = ModelValidationRequestRef(profile="default")
        report = ModelValidationReport.from_findings(findings=(), request=req)
        with pytest.raises(Exception):
            report.overall_status = "FAIL"  # type: ignore[misc]

    def test_provenance_populated(self) -> None:
        """Provenance records validators_run and request_id."""
        req = ModelValidationRequestRef(profile="default")
        report = ModelValidationReport.from_findings(
            findings=(),
            request=req,
            validators_run=("v1", "v2"),
            request_id="req-abc",
        )
        assert report.provenance.validators_run == ("v1", "v2")
        assert report.provenance.request_id == "req-abc"

    def test_json_serialisable(self) -> None:
        """ValidationReport serialises to JSON without custom encoders."""
        req = ModelValidationRequestRef(profile="default")
        findings = (
            _embed("naming", "FAIL", "Bad name"),
            _embed("typing", "WARN", "Missing type"),
        )
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        data = json.loads(report.model_dump_json())
        assert data["overall_status"] == "FAIL"
        assert len(data["findings"]) == 2

    def test_inconsistent_overall_status_rejected(self) -> None:
        """Direct construction with wrong overall_status raises ValueError."""
        with pytest.raises(Exception):
            ModelValidationReport(
                profile="default",
                overall_status="PASS",  # wrong — findings have FAIL
                findings=(_embed("v", "FAIL"),),
            )

    def test_report_id_is_unique(self) -> None:
        """Each report gets a unique UUID."""
        req = ModelValidationRequestRef(profile="default")
        r1 = ModelValidationReport.from_findings(findings=(), request=req)
        r2 = ModelValidationReport.from_findings(findings=(), request=req)
        assert r1.report_id != r2.report_id

    def test_error_dominates_all_other_severities(self) -> None:
        """ERROR finding produces ERROR overall_status regardless of others."""
        req = ModelValidationRequestRef(profile="default")
        findings = (
            _embed("v", "PASS"),
            _embed("v", "WARN"),
            _embed("v", "FAIL"),
            _embed("v", "ERROR"),
        )
        report = ModelValidationReport.from_findings(findings=findings, request=req)
        assert report.overall_status == "ERROR"


# ---------------------------------------------------------------------------
# ValidationMetrics standalone
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationMetrics:
    """Tests for ValidationMetrics standalone construction."""

    def test_default_construction(self) -> None:
        m = ModelValidationMetrics()
        assert m.total == 0
        assert m.pass_count == 0

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelValidationMetrics(total=-1)
