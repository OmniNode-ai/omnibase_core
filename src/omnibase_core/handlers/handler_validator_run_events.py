# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerValidatorRunEvents — a validation report becomes run and fire events.

RULING 2026-10-14T20:01:09Z (OMN-17427): "move things to generic validators that
trigger events ... when they're triggered, so we know when CI is useful."

Pure COMPUTE handler: one ``run`` event for the report, then one ``fire`` event
for each WARN, FAIL or ERROR finding. PASS, SKIP and NOT_APPLICABLE findings do
not fire. A report with no findings still yields its ``run`` event, because a
check that never ran is as useless as one that never fires.
"""

from __future__ import annotations

from typing import Final, Literal

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.models.validation.model_validator_run_events import (
    ModelValidatorRunEvents,
)

__all__ = ["HandlerValidatorRunEvents"]

_FIRING: Final[dict[str, Literal["WARN", "FAIL", "ERROR"]]] = {
    "WARN": "WARN",
    "FAIL": "FAIL",
    "ERROR": "ERROR",
}


class HandlerValidatorRunEvents:
    """Derive the run and fire events of one canonical validation report."""

    def handle(self, request: ModelValidationReport) -> ModelValidatorRunEvents:
        validator_name = ",".join(request.provenance.validators_run)
        emitted_at = request.provenance.generated_at
        fires: list[ModelValidatorRunEvent] = []
        for finding in request.findings:
            severity = _FIRING.get(finding.severity)
            if severity is not None:
                fires.append(
                    ModelValidatorRunEvent(
                        kind="fire",
                        validator_name=finding.validator_id,
                        report_ref=request.report_id,
                        emitted_at=emitted_at,
                        severity=severity,
                        rule_name=finding.rule_id or finding.validator_id,
                        location=finding.location,
                    )
                )
        run = ModelValidatorRunEvent(
            kind="run",
            validator_name=validator_name,
            report_ref=request.report_id,
            emitted_at=emitted_at,
            verdict=request.overall_status,
            fired_count=len(fires),
        )
        return ModelValidatorRunEvents(events=(run, *fires))
