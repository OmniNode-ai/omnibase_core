# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``ci_summary_verdict`` (OMN-17864).

Facts in (the rows the CI Summary job observed: jobs and external check-runs, the observation time and
the poll deadline; or one file's text for the parity rule), ``ModelValidationIssue`` out. Every name,
conclusion set, window and message is a ``parameters`` entry of the rule rows of
``contracts/ci_summary_verdict.validation.yaml``. An error issue is a red verdict, a warning issue
(``pending_severity``) is a pending verdict. No file read, no clock: ``observed_at`` is a row fact.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

RULE_JOBS = "ci_summary_jobs"
RULE_EXTERNAL = "ci_summary_external"
RULE_PARITY = "ci_summary_gate_parity"


def _stamp(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _issue(
    row: ModelValidatorRule, path: Path, message: str, *, pending: bool
) -> ModelValidationIssue:
    severity = (
        EnumSeverity(rule_string(row, "pending_severity")) if pending else row.severity
    )
    return ModelValidationIssue(
        severity=severity,
        message=message,
        code=row.rule_id,
        file_path=path,
        rule_name=row.rule_id,
    )


def _latest(rows: object) -> dict[str, Mapping[str, Any]]:
    """The newest row per name: a rerun's row replaces the attempt it superseded."""
    latest: dict[str, Mapping[str, Any]] = {}
    if not isinstance(rows, list):
        return latest
    for raw in rows:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("name"), str):
            continue
        name = raw["name"]
        held = latest.get(name)
        key = (str(raw.get("completed_at") or ""), str(raw.get("started_at") or ""))
        if held is None or key >= (
            str(held.get("completed_at") or ""),
            str(held.get("started_at") or ""),
        ):
            latest[name] = raw
    return latest


def _past_deadline(facts: Mapping[str, Any]) -> bool:
    observed, deadline = (
        _stamp(facts.get("observed_at")),
        _stamp(facts.get("deadline_at")),
    )
    return observed is not None and deadline is not None and observed >= deadline


def check_rows(
    path: Path, facts: Mapping[str, Any], rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """The verdict of one rows file: jobs rule then external rule."""
    return check_jobs(path, facts, rules) + check_external(path, facts, rules)


def check_jobs(
    path: Path, facts: Mapping[str, Any], rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    row = rules.get(RULE_JOBS)
    if row is None or not row.enabled:
        return ()
    self_name = rule_string(row, "self_name")
    good = set(rule_strings(row, "good_conclusions"))
    soft = set(rule_strings(row, "soft_allowlist"))
    strict = rule_strings(row, "strict_success_jobs")
    expired = _past_deadline(facts)
    latest = _latest(facts.get("jobs"))
    issues: list[ModelValidationIssue] = []
    for name in sorted(latest):
        state = latest[name]
        status, conclusion = str(state.get("status")), str(state.get("conclusion"))
        if name == self_name or name in soft:
            continue
        if status != "completed":
            template = "deadline_message" if expired else "pending_message"
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, template).format(name=name, status=status),
                    pending=not expired,
                )
            )
        elif conclusion not in good:
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, "red_message").format(
                        name=name, conclusion=conclusion
                    ),
                    pending=False,
                )
            )
    for name in strict:
        held = latest.get(name)
        if held is None:
            template = "deadline_message" if expired else "missing_message"
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, template).format(name=name, status="absent"),
                    pending=not expired,
                )
            )
        elif held.get("status") == "completed" and held.get("conclusion") != "success":
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, "strict_message").format(
                        name=name, conclusion=held.get("conclusion")
                    ),
                    pending=False,
                )
            )
    return tuple(issues)


def check_external(
    path: Path, facts: Mapping[str, Any], rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    row = rules.get(RULE_EXTERNAL)
    if row is None or not row.enabled:
        return ()
    expected = rule_strings(row, "expected_contexts")
    supersedable = set(rule_strings(row, "supersedable_conclusions"))
    grace = rule_int(row, "supersession_grace_s")
    observed = _stamp(facts.get("observed_at"))
    expired = _past_deadline(facts)
    latest = _latest(facts.get("check_runs"))
    issues: list[ModelValidationIssue] = []
    for name in expected:
        state = latest.get(name)
        status = "absent" if state is None else str(state.get("status"))
        if state is None or status != "completed":
            template = "deadline_message" if expired else "pending_message"
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, template).format(name=name, status=status),
                    pending=not expired,
                )
            )
            continue
        conclusion = str(state.get("conclusion"))
        if conclusion == "success":
            continue
        completed = _stamp(state.get("completed_at"))
        age = (
            None
            if observed is None or completed is None
            else int((observed - completed).total_seconds())
        )
        if (
            conclusion in supersedable
            and age is not None
            and -grace <= age <= grace
            and not expired
        ):
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, "provisional_message").format(
                        name=name, conclusion=conclusion, age_s=age, grace_s=grace
                    ),
                    pending=True,
                )
            )
        else:
            issues.append(
                _issue(
                    row,
                    path,
                    rule_string(row, "red_message").format(
                        name=name, conclusion=conclusion
                    ),
                    pending=False,
                )
            )
    return tuple(issues)


def check_parity(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """One issue per gate-copy marker a file that is not the generic validator itself carries."""
    row = rules.get(RULE_PARITY)
    if row is None or not row.enabled:
        return ()
    posix = path.as_posix()
    if any(re.search(p, posix) for p in rule_strings(row, "owner_path_patterns")):
        return ()
    template = rule_string(row, "message")
    for marker in rule_strings(row, "copy_markers"):
        found = re.search(marker, source)
        if found:
            line = source.count("\n", 0, found.start()) + 1
            return (
                ModelValidationIssue(
                    severity=row.severity,
                    message=template.format(marker=marker),
                    code=row.rule_id,
                    file_path=path,
                    line_number=line,
                    rule_name=row.rule_id,
                ),
            )
    return ()


__all__ = [
    "RULE_EXTERNAL",
    "RULE_JOBS",
    "RULE_PARITY",
    "check_external",
    "check_jobs",
    "check_parity",
    "check_rows",
]
