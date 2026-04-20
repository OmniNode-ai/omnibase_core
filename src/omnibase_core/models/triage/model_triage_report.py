# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTriageReport + rank_findings utility (OMN-9322)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_triage_probe_status import EnumProbeStatus
from omnibase_core.enums.enum_triage_severity import EnumTriageSeverity
from omnibase_core.models.triage.model_triage_finding import ModelTriageFinding
from omnibase_core.models.triage.model_triage_probe_result import ModelTriageProbeResult


class ModelTriageReport(BaseModel):
    """Aggregate report emitted by the full-triage orchestrator.

    `ranked_findings` is a flat, deterministically-sorted list of every finding
    from every probe, newest-highest-severity-broadest-blast first.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(description="Unique identifier for this triage run")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when orchestrator began fan-out",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when aggregation finished",
    )
    probe_results: list[ModelTriageProbeResult] = Field(default_factory=list)
    ranked_findings: list[ModelTriageFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_time_window(self) -> ModelTriageReport:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")
        return self

    @property
    def total_duration_ms(self) -> int:
        return int((self.completed_at - self.started_at).total_seconds() * 1000)

    @property
    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in EnumTriageSeverity}
        for finding in self.ranked_findings:
            counts[finding.severity.value] += 1
        return counts

    @property
    def probe_status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in EnumProbeStatus}
        for probe in self.probe_results:
            counts[probe.status.value] += 1
        return counts


def rank_findings(findings: list[ModelTriageFinding]) -> list[ModelTriageFinding]:
    """Return findings sorted by rank_score descending, ties broken deterministically."""
    return sorted(
        findings,
        key=lambda f: (-f.rank_score, f.source_probe, f.message),
    )
