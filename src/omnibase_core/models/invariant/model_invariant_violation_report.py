"""Model for invariant violation report aggregation."""

from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_invariant_report_status import EnumInvariantReportStatus
from omnibase_core.models.invariant.model_invariant_violation_detail import (
    ModelInvariantViolationDetail,
)

# Severity ordering for comparison (lower = less severe)
_SEVERITY_ORDER: dict[EnumSeverity, int] = {
    EnumSeverity.DEBUG: 0,
    EnumSeverity.INFO: 1,
    EnumSeverity.WARNING: 2,
    EnumSeverity.ERROR: 3,
    EnumSeverity.CRITICAL: 4,
    EnumSeverity.FATAL: 5,
}


def _severity_gte(a: EnumSeverity, b: EnumSeverity) -> bool:
    """Check if severity a >= severity b."""
    return _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0)


class ModelInvariantViolationReport(BaseModel):
    """Comprehensive report of all invariant violations from an evaluation run.

    Reports facts only - does not embed policy decisions about blocking.
    The calling code (via contract configuration) determines what severity
    threshold constitutes a blocking violation.

    Note on failed_count vs len(violations):
        The `failed_count` field represents the total count of failed invariants,
        while the `violations` list contains detailed violation records. These are
        intentionally independent because:
        - Some evaluations may summarize failures without generating full detail records
        - The violations list may be a filtered subset (e.g., only CRITICAL violations)
        - Pagination or truncation may limit the violations list while preserving counts
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identification
    id: UUID = Field(default_factory=uuid4)
    evaluation_id: UUID = Field(..., description="Links to the evaluation run")
    invariant_set_id: UUID = Field(
        ..., description="The invariant set that was evaluated"
    )
    target: str = Field(..., description="Node/workflow that was evaluated")

    # Timing
    evaluated_at: datetime = Field(
        ...,
        description="Timestamp when evaluation completed. Timezone-aware recommended (UTC preferred).",
    )
    duration_ms: float = Field(
        ..., ge=0, description="Evaluation duration in milliseconds"
    )

    # Summary Statistics (stored, not computed - set by creator)
    total_invariants: int = Field(..., ge=0)
    passed_count: int = Field(..., ge=0)
    failed_count: int = Field(
        ...,
        ge=0,
        description="Total count of failed invariants. Independent from len(violations) "
        "which may be a filtered subset or omit details for summarized failures.",
    )
    skipped_count: int = Field(..., ge=0)

    # Status
    status: EnumInvariantReportStatus

    # Violations (detailed)
    violations: list[ModelInvariantViolationDetail] = Field(default_factory=list)

    # Context
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_count_consistency(self) -> Self:
        """Validate that count fields are internally consistent."""
        expected_total = self.passed_count + self.failed_count + self.skipped_count
        if self.total_invariants != expected_total:
            msg = (
                f"Count mismatch: total_invariants ({self.total_invariants}) != "
                f"passed_count ({self.passed_count}) + failed_count ({self.failed_count}) "
                f"+ skipped_count ({self.skipped_count}) = {expected_total}"
            )
            raise ValueError(msg)
        return self

    # Computed Properties
    # NOTE(OMN-1206): Pydantic @computed_field requires @property below it, causing mypy prop-decorator warning.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def pass_rate(self) -> float:
        """Pass rate from 0.0 to 1.0. Returns 1.0 if no invariants."""
        if self.total_invariants == 0:
            return 1.0
        return self.passed_count / self.total_invariants

    # NOTE(OMN-1206): Pydantic @computed_field requires @property below it, causing mypy prop-decorator warning.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def critical_count(self) -> int:
        """Count of CRITICAL severity violations."""
        return sum(1 for v in self.violations if v.severity == EnumSeverity.CRITICAL)

    # NOTE(OMN-1206): Pydantic @computed_field requires @property below it, causing mypy prop-decorator warning.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def warning_count(self) -> int:
        """Count of WARNING severity violations."""
        return sum(1 for v in self.violations if v.severity == EnumSeverity.WARNING)

    # NOTE(OMN-1206): Pydantic @computed_field requires @property below it, causing mypy prop-decorator warning.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def info_count(self) -> int:
        """Count of INFO severity violations."""
        return sum(1 for v in self.violations if v.severity == EnumSeverity.INFO)

    # Query Methods (no policy, just filtering)
    def get_violations_by_severity(
        self, severity: EnumSeverity
    ) -> list[ModelInvariantViolationDetail]:
        """Filter violations by exact severity level."""
        return [v for v in self.violations if v.severity == severity]

    def get_violations_at_or_above(
        self, threshold: EnumSeverity
    ) -> list[ModelInvariantViolationDetail]:
        """Get violations at or above the given severity threshold."""
        return [v for v in self.violations if _severity_gte(v.severity, threshold)]

    def has_violations_at_or_above(self, threshold: EnumSeverity) -> bool:
        """Check if any violations meet or exceed the threshold.

        Used by callers to determine blocking based on contract-defined policy.
        """
        return any(_severity_gte(v.severity, threshold) for v in self.violations)

    def to_summary_dict(self) -> dict[str, str | int | float | bool]:
        """Compact summary with JSON-safe primitives only."""
        return {
            "id": str(self.id),
            "evaluation_id": str(self.evaluation_id),
            "invariant_set_id": str(self.invariant_set_id),
            "target": self.target,
            "status": self.status.value,
            "total_invariants": self.total_invariants,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "pass_rate": round(self.pass_rate, 4),
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "duration_ms": self.duration_ms,
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Deterministic markdown report for logs/PR comments."""
        lines = [
            "# Invariant Evaluation Report",
            "",
            f"**Target**: {self.target}",
            f"**Evaluated**: {self.evaluated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Duration**: {self.duration_ms:.1f}ms",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Invariants | {self.total_invariants} |",
            f"| Passed | {self.passed_count} |",
            f"| Failed | {self.failed_count} |",
            f"| Skipped | {self.skipped_count} |",
            f"| Pass Rate | {self.pass_rate:.1%} |",
            f"| Critical | {self.critical_count} |",
            f"| Warnings | {self.warning_count} |",
            f"| Info | {self.info_count} |",
            "",
            f"**Status**: {self.status.value.upper()}",
            "",
        ]

        # Group violations by severity
        critical = self.get_violations_by_severity(EnumSeverity.CRITICAL)
        warnings = self.get_violations_by_severity(EnumSeverity.WARNING)
        info = self.get_violations_by_severity(EnumSeverity.INFO)

        if critical:
            lines.append("## Critical Failures")
            lines.append("")
            for v in critical:
                lines.append(f"### {v.invariant_name}")
                lines.append(f"- **Message**: {v.message}")
                if v.field_path:
                    lines.append(f"- **Field**: {v.field_path}")
                lines.append("")

        if warnings:
            lines.append("## Warnings")
            lines.append("")
            for v in warnings:
                lines.append(f"### {v.invariant_name}")
                lines.append(f"- **Message**: {v.message}")
                if v.field_path:
                    lines.append(f"- **Field**: {v.field_path}")
                lines.append("")

        if info:
            lines.append("## Info")
            lines.append("")
            for v in info:
                lines.append(f"### {v.invariant_name}")
                lines.append(f"- **Message**: {v.message}")
                if v.field_path:
                    lines.append(f"- **Field**: {v.field_path}")
                lines.append("")

        if not self.violations:
            lines.append("## Violations")
            lines.append("")
            lines.append("No violations detected.")
            lines.append("")

        return "\n".join(lines)


__all__ = ["ModelInvariantViolationReport"]
