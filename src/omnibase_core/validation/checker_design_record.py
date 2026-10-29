# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure design-record predicate ported from omnimarket (OMN-21509, OMN-21460).

Field labels, header substrings, empty detector values, severity levels, and
recognition of the contract's gap pattern come from the supplied subcontract.
"""

from __future__ import annotations

import re

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.design_record.model_design_record_check_input import (
    ModelDesignRecordCheckInput,
)
from omnibase_core.models.design_record.model_design_record_check_result import (
    ModelDesignRecordCheckResult,
)
from omnibase_core.models.design_record.model_design_record_rules import (
    ModelDesignRecordRules,
)

__all__ = ["check_design_record"]


def _field(text: str, key: str) -> str:
    pattern = re.compile(
        rf"^[ \t]*(?:[-*][ \t]+)?\**{re.escape(key)}\**[ \t]*:\**[ \t]*(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip().strip("`*").strip() if match else ""


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"[\s|:\-]+", line)) and "-" in line


def _find_table(
    lines: list[str], rules: ModelDesignRecordRules
) -> tuple[list[str], list[list[str]]] | None:
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = [cell.lower() for cell in _cells(line)]
        if not (
            any(rules.mode_column in cell for cell in header)
            and any(rules.severity_column in cell for cell in header)
            and any(rules.detector_column in cell for cell in header)
        ):
            continue
        rows: list[list[str]] = []
        for body in lines[index + 1 :]:
            if not body.lstrip().startswith("|"):
                break
            if _is_separator(body):
                continue
            rows.append(_cells(body))
        return header, rows
    return None


def check_design_record(
    request: ModelDesignRecordCheckInput,
) -> ModelDesignRecordCheckResult:
    """Check a record using only the supplied text and contract."""
    rules = ModelDesignRecordRules.from_contract(request.contract)
    gap = re.compile(rules.gap_pattern)
    text = request.text
    lines = text.splitlines()
    issues: list[ModelValidationIssue] = []

    def add(code: str, row: int | None = None, row_severity: str = "") -> None:
        enabled, severity, message, part = rules.configuration(code)
        if not enabled:
            return
        context = {"part": part}
        if row is not None:
            context["row"] = str(row)
        issues.append(
            ModelValidationIssue(
                severity=severity,
                message=message.format(
                    number=row,
                    levels=", ".join(str(v) for v in rules.severity_levels),
                    severity=row_severity,
                ),
                code=code,
                rule_name=code,
                context=context,
            )
        )

    command = _field(text, rules.live_check_command_label)
    failing = _field(text, rules.live_check_failing_label)
    intended = _field(text, rules.intended_state_label)
    table = _find_table(lines, rules)

    if not (command or failing or intended or table):
        add("record_missing")
    else:
        if not intended:
            add("intended_state_missing")
        if not command:
            add("live_check_command_missing")

    rows: list[list[str]] = []
    uncovered = 0
    if table is None:
        if intended or command or failing:
            add("failure_mode_table_missing")
    else:
        header, rows = table
        if not rows:
            add("failure_mode_table_empty")
        sev_col = next(i for i, c in enumerate(header) if rules.severity_column in c)
        det_col = max(i for i, c in enumerate(header) if rules.detector_column in c)
        for number, cells in enumerate(rows, start=1):
            detector = cells[det_col] if det_col < len(cells) else ""
            if detector.strip(
                "`* "
            ).lower() in rules.empty_detector_values and not gap.search(
                " ".join(cells)
            ):
                uncovered += 1
                add("row_without_detector_or_gap", number)
            severity = cells[sev_col].strip("`* ") if sev_col < len(cells) else ""
            if not severity.isdigit() or int(severity) not in rules.severity_levels:
                add("severity_out_of_range", number, severity)

    return ModelDesignRecordCheckResult(
        issues=tuple(issues),
        exit_code=1
        if any(issue.severity.is_error_or_above() for issue in issues)
        else 0,
        record_issue_count=len(issues),
        failure_mode_rows=len(rows),
        rows_without_detector_or_gap=uncovered,
        live_check_command_present=bool(command),
        live_check_failing_reading=bool(failing),
    )
