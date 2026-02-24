# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidationReport model — aggregated result from one or more validators.

Part of the Generic Validator Node Architecture (OMN-2362).

Aggregates ValidationFinding instances into a machine-readable result with
overall_status, metrics, and provenance. Status precedence and profile
semantics are encoded as an explicit lookup, not scattered logic.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Status precedence matrix (OMN-2543 requirement)
# "Status precedence must be explicitly encoded as a lookup (not implicit)"
# Priority order: ERROR > FAIL > WARN > PASS
# SKIP and NOT_APPLICABLE do not influence aggregate overall_status.
# ---------------------------------------------------------------------------
_SEVERITY_PRECEDENCE: dict[str, int] = {
    "ERROR": 40,
    "FAIL": 30,
    "WARN": 20,
    "PASS": 10,
    # SKIP and NOT_APPLICABLE intentionally absent — they do not contribute.
}

# The overall_status literals that map out of the precedence matrix.
# These are a subset of finding severity literals (no SKIP/NOT_APPLICABLE).
_PRECEDENCE_TO_STATUS: dict[int, Literal["PASS", "WARN", "FAIL", "ERROR"]] = {
    40: "ERROR",
    30: "FAIL",
    20: "WARN",
    10: "PASS",
}


def _compute_overall_status(
    findings: tuple[ValidationFindingRef, ...],
    profile: Literal["strict", "default", "advisory"],
) -> Literal["PASS", "WARN", "FAIL", "ERROR"]:
    """Compute overall_status from findings using the explicit precedence matrix.

    Profile semantics:
    - 'strict': WARN is elevated to FAIL before precedence lookup.
    - 'default': findings are evaluated at face value.
    - 'advisory': result is capped at WARN; never FAIL or ERROR.

    SKIP and NOT_APPLICABLE severities are excluded from the computation.
    When there are no contributing findings the result is PASS.
    """
    highest_precedence = _SEVERITY_PRECEDENCE["PASS"]

    for finding in findings:
        severity = finding.severity
        # SKIP and NOT_APPLICABLE do not contribute to overall_status.
        if severity not in _SEVERITY_PRECEDENCE:
            continue
        # 'strict' profile: elevate WARN to FAIL.
        if profile == "strict" and severity == "WARN":
            severity = "FAIL"
        precedence = _SEVERITY_PRECEDENCE[severity]
        highest_precedence = max(highest_precedence, precedence)

    raw_status = _PRECEDENCE_TO_STATUS[highest_precedence]

    # 'advisory' profile: cap at WARN (never FAIL or ERROR).
    if profile == "advisory" and raw_status in ("FAIL", "ERROR"):
        return "WARN"

    return raw_status


# ---------------------------------------------------------------------------
# ValidationFindingRef — lightweight reference used by the precedence function
# ---------------------------------------------------------------------------


class ValidationFindingRef(BaseModel):
    """Lightweight reference used inside ValidationReport.

    Stores only the fields needed for status aggregation and metrics.
    Full ValidationFinding objects should be stored externally and
    referenced here by index or validator_id when needed.

    Note: ValidationReport embeds ValidationFinding directly (not via reference)
    for full self-containment and JSON serializability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    severity: Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"] = (
        Field(
            description="Severity of this finding (mirrors ValidationFinding.severity).",
        )
    )

    validator_id: str = Field(
        description="Validator that produced this finding.",
    )


# ---------------------------------------------------------------------------
# ValidationFindingEmbed — full finding fields inlined in ValidationReport.
# Defined before ValidationReport to avoid forward-reference issues.
# ---------------------------------------------------------------------------


class ValidationFindingEmbed(BaseModel):
    """Full ValidationFinding fields embedded inside ValidationReport.

    Mirrors the fields of ValidationFinding exactly. We define this here
    (rather than importing ValidationFinding) to avoid circular imports
    between model_validation_report and model_validation_finding.
    Callers should construct these from ValidationFinding instances:
        ValidationFindingEmbed(**finding.model_dump())
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validator_id: str = Field(description="Validator that produced this finding.")
    severity: Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"] = (
        Field(
            description="Severity of this finding.",
        )
    )
    location: str | None = Field(default=None, description="File/line location.")
    message: str = Field(description="Human-readable description of the finding.")
    remediation: str | None = Field(default=None, description="How to fix the issue.")
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured machine-readable evidence.",
    )
    rule_id: str | None = Field(
        default=None,
        description="Rule within the validator that produced this finding.",
    )


# ---------------------------------------------------------------------------
# ValidationRequestRef — minimal duck-type accepted by ValidationReport.from_findings
# ---------------------------------------------------------------------------


class ValidationRequestRef(BaseModel):
    """Minimal duck-type of ValidationRequest used by ValidationReport.from_findings.

    Allows the factory to accept a real ValidationRequest or any compatible
    object without a hard import dependency.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    profile: Literal["strict", "default", "advisory"] = Field(
        description="Profile from the triggering request.",
    )


# ---------------------------------------------------------------------------
# ValidationMetrics
# ---------------------------------------------------------------------------


class ValidationMetrics(BaseModel):
    """Summary counts of findings by severity.

    All counts are non-negative. The sum of all severity counts equals the
    total number of findings in the parent ValidationReport.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total: int = Field(default=0, description="Total number of findings.", ge=0)
    pass_count: int = Field(default=0, description="Findings with severity PASS.", ge=0)
    warn_count: int = Field(default=0, description="Findings with severity WARN.", ge=0)
    fail_count: int = Field(default=0, description="Findings with severity FAIL.", ge=0)
    error_count: int = Field(
        default=0, description="Findings with severity ERROR.", ge=0
    )
    skip_count: int = Field(default=0, description="Findings with severity SKIP.", ge=0)
    not_applicable_count: int = Field(
        default=0, description="Findings with severity NOT_APPLICABLE.", ge=0
    )


# ---------------------------------------------------------------------------
# ValidationProvenance
# ---------------------------------------------------------------------------


class ValidationProvenance(BaseModel):
    """Provenance metadata for a validation run.

    Records when the report was generated, which request triggered it,
    and the schema version so consumers can interpret the report correctly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    generated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat(),
        description="ISO-8601 timestamp (UTC) when this report was generated.",
    )

    request_id: str | None = Field(
        default=None,
        description=(
            "Correlation ID linking this report back to the ValidationRequest "
            "that triggered the run. Caller-supplied."
        ),
    )

    schema_version: str = Field(
        default="1.0",
        description=(
            "Version of the ValidationReport schema. Used for forward-compat "
            "parsing. Follows semver major.minor format."
        ),
    )

    validators_run: tuple[str, ...] = Field(
        default=(),
        description="Ordered list of validator IDs that were invoked for this run.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_metrics(
    findings: tuple[ValidationFindingEmbed, ...],
) -> ValidationMetrics:
    """Build ValidationMetrics by counting findings by severity."""
    counts: dict[str, int] = {
        "PASS": 0,
        "WARN": 0,
        "FAIL": 0,
        "ERROR": 0,
        "SKIP": 0,
        "NOT_APPLICABLE": 0,
    }
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    return ValidationMetrics(
        total=len(findings),
        pass_count=counts["PASS"],
        warn_count=counts["WARN"],
        fail_count=counts["FAIL"],
        error_count=counts["ERROR"],
        skip_count=counts["SKIP"],
        not_applicable_count=counts["NOT_APPLICABLE"],
    )


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class ValidationReport(BaseModel):
    """Aggregates ValidationFinding instances into a machine-readable result.

    overall_status is computed from findings using an explicit precedence matrix:
        ERROR > FAIL > WARN > PASS
    SKIP and NOT_APPLICABLE do not influence overall_status.

    Profile modifiers applied during computation:
    - 'strict': WARN is elevated to FAIL.
    - 'advisory': result is capped at WARN; never FAIL or ERROR.
    - 'default': findings evaluated at face value.

    The report is fully JSON-serialisable without custom encoders.

    Example:
        >>> from omnibase_core.models.validation.model_validation_finding import (
        ...     ValidationFinding,
        ... )
        >>> from omnibase_core.models.validation.model_validation_request import (
        ...     ValidationRequest,
        ... )
        >>> req = ValidationRequest(target="src/", scope="subtree", profile="strict")
        >>> finding = ValidationFinding(
        ...     validator_id="naming_convention",
        ...     severity="WARN",
        ...     message="Module name does not match convention.",
        ... )
        >>> report = ValidationReport.from_findings(
        ...     findings=(ValidationFindingEmbed(**finding.model_dump()),),
        ...     request=ValidationRequestRef(profile=req.profile),
        ... )
        >>> report.overall_status  # strict profile elevates WARN -> FAIL
        'FAIL'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID uniquely identifying this report instance.",
    )

    profile: Literal["strict", "default", "advisory"] = Field(
        description=(
            "Validation profile used when computing overall_status. "
            "Must match the profile from the triggering ValidationRequest."
        ),
    )

    overall_status: Literal["PASS", "WARN", "FAIL", "ERROR"] = Field(
        description=(
            "Aggregated status derived from all findings via the explicit "
            "precedence matrix (ERROR > FAIL > WARN > PASS). "
            "SKIP and NOT_APPLICABLE findings do not contribute. "
            "Profile modifiers are applied before the lookup."
        ),
    )

    findings: tuple[ValidationFindingEmbed, ...] = Field(
        default=(),
        description="All findings produced during this validation run.",
    )

    metrics: ValidationMetrics = Field(
        default_factory=ValidationMetrics,
        description="Summary counts of findings by severity.",
    )

    provenance: ValidationProvenance = Field(
        default_factory=ValidationProvenance,
        description="Metadata about when and how this report was generated.",
    )

    @model_validator(mode="after")
    def _validate_overall_status_consistent(self) -> ValidationReport:
        """Validate that overall_status is consistent with findings and profile.

        This is a read-time guard; callers should use from_findings() to
        ensure consistency at construction time.
        """
        refs = tuple(
            ValidationFindingRef(
                severity=f.severity,
                validator_id=f.validator_id,
            )
            for f in self.findings
        )
        expected = _compute_overall_status(refs, self.profile)
        if self.overall_status != expected:
            raise ValueError(
                f"overall_status '{self.overall_status}' is inconsistent with findings "
                f"under profile '{self.profile}'. Expected '{expected}'."
            )
        return self

    @classmethod
    def from_findings(
        cls,
        findings: tuple[ValidationFindingEmbed, ...],
        request: ValidationRequestRef,
        validators_run: tuple[str, ...] = (),
        request_id: str | None = None,
    ) -> ValidationReport:
        """Construct a ValidationReport by computing overall_status from findings.

        This is the canonical factory method. It:
        1. Builds ValidationFindingRef objects for the precedence computation.
        2. Runs _compute_overall_status with the given profile.
        3. Builds ValidationMetrics from the findings.
        4. Returns a fully populated, frozen ValidationReport.

        Args:
            findings: All findings produced during the validation run.
            request: The ValidationRequest (or compatible duck-type) that triggered the run.
            validators_run: Ordered list of validator IDs that were invoked.
            request_id: Optional caller-supplied correlation ID.

        Returns:
            A frozen ValidationReport with consistent overall_status.
        """
        refs = tuple(
            ValidationFindingRef(
                severity=f.severity,
                validator_id=f.validator_id,
            )
            for f in findings
        )
        overall = _compute_overall_status(refs, request.profile)

        metrics = _build_metrics(findings)

        provenance = ValidationProvenance(
            validators_run=validators_run,
            request_id=request_id,
        )

        return cls(
            profile=request.profile,
            overall_status=overall,
            findings=findings,
            metrics=metrics,
            provenance=provenance,
        )


# Re-export the precedence matrix constant so other modules can reference it.
SEVERITY_PRECEDENCE = _SEVERITY_PRECEDENCE

__all__ = [
    "SEVERITY_PRECEDENCE",
    "ValidationFindingEmbed",
    "ValidationFindingRef",
    "ValidationMetrics",
    "ValidationProvenance",
    "ValidationReport",
    "ValidationRequestRef",
    "_build_metrics",
    "_compute_overall_status",
]
