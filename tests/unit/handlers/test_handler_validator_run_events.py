# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerValidatorRunEvents turns a validation report into run and fire events.

RULING 2026-10-14T20:01:09Z (OMN-17427): generic validators trigger events when
they run and when they fire, so the work ledger can answer which checks ever
catch anything.
"""

from __future__ import annotations

from typing import Literal

import pytest

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_run_events import (
    HandlerValidatorRunEvents,
)

pytestmark = pytest.mark.unit


def _report(*findings: ModelValidationFindingEmbed) -> ModelValidationReport:
    return ModelValidationReport.from_findings(
        findings=findings,
        request=ModelValidationRequestRef(profile="default"),
        validators_run=("arch-example",),
    )


def _finding(
    severity: Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "NOT_APPLICABLE"],
    rule_id: str | None = None,
    location: str | None = None,
) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id="arch-example",
        severity=severity,
        rule_id=rule_id,
        location=location,
        message=f"{severity} finding",
    )


def test_failing_report_emits_one_run_event_and_one_fire_event_per_finding() -> None:
    report = _report(
        _finding("FAIL", rule_id="rule-a", location="a.py:1"),
        _finding("WARN", rule_id="rule-b"),
    )

    result = HandlerValidatorRunEvents().handle(report)

    run = [e for e in result.events if e.kind == "run"]
    fire = [e for e in result.events if e.kind == "fire"]
    assert len(run) == 1
    assert run[0].verdict == "FAIL"
    assert run[0].validator_name == "arch-example"
    assert run[0].report_ref == report.report_id
    assert run[0].fired_count == 2
    assert [(e.rule_name, e.severity, e.location) for e in fire] == [
        ("rule-a", "FAIL", "a.py:1"),
        ("rule-b", "WARN", None),
    ]


def test_passing_report_emits_the_run_event_and_no_fire_event() -> None:
    # Negative control: a check that found nothing still reports that it ran
    # (a check that never runs is not "useful"), and it never fires.
    result = HandlerValidatorRunEvents().handle(_report(_finding("PASS")))

    assert [e.kind for e in result.events] == ["run"]
    assert result.events[0].verdict == "PASS"
    assert result.events[0].fired_count == 0


def test_skip_and_not_applicable_findings_do_not_fire() -> None:
    result = HandlerValidatorRunEvents().handle(
        _report(_finding("SKIP"), _finding("NOT_APPLICABLE"), _finding("ERROR"))
    )

    fire = [e for e in result.events if e.kind == "fire"]
    assert [e.severity for e in fire] == ["ERROR"]
    assert result.events[0].fired_count == 1


def test_fire_event_without_a_rule_id_names_the_validator() -> None:
    result = HandlerValidatorRunEvents().handle(_report(_finding("FAIL")))

    fire = [e for e in result.events if e.kind == "fire"]
    assert [e.rule_name for e in fire] == ["arch-example"]


def test_empty_report_still_emits_the_run_event() -> None:
    result = HandlerValidatorRunEvents().handle(_report())

    assert [e.kind for e in result.events] == ["run"]
