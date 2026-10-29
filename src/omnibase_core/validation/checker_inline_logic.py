# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure inline-logic checker: facts in, ``ModelValidationIssue`` out (OMN-21534, K9).

Logic belongs in a node or a core hook, not in a workflow ``run:`` block or a contract
``check_value``. This module judges parsed run steps and check values against rule rows
of ``contracts/inline_logic.validation.yaml``. Every pattern, line threshold, character
threshold and remediation text is a ``parameters`` entry of a rule row; nothing here
names a language, a shell or a limit. The module performs no I/O: no file read, no
clock, no environment.

Rule row kinds (the ``kind`` parameter):

* ``run_step_signal`` -- a ``run:`` step fires when ``shell_pattern`` matches its
  effective shell or ``run_pattern`` matches its script (at least one is required).
* ``run_block_length`` -- a ``run:`` step fires when its script holds more than
  ``max_run_lines`` non-blank lines.
* ``check_value_program`` -- a ``check_value`` fires when ``program_pattern`` matches
  and the value is longer than ``max_inline_chars`` or, with ``refuse_newline``, holds
  a newline.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.inline_logic.model_inline_logic_check_value import (
    ModelInlineLogicCheckValue,
)
from omnibase_core.models.inline_logic.model_inline_logic_run_step import (
    ModelInlineLogicRunStep,
)

__all__ = ["check_inline_logic"]


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"inline_logic rule {rule.rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def _text(rule: ModelValidatorRule, key: str, *, required: bool) -> str:
    value = (rule.parameters or {}).get(key)
    if value is None:
        if required:
            raise _invalid(rule, f"parameter {key!r} is required")
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise _invalid(rule, f"parameter {key!r} must be a non-empty string")
    return value


def _pattern(
    rule: ModelValidatorRule, key: str, *, required: bool
) -> re.Pattern[str] | None:
    text = _text(rule, key, required=required)
    if not text:
        return None
    try:
        return re.compile(text)
    except re.error as exc:
        raise _invalid(
            rule, f"parameter {key!r} is not a regular expression: {exc}"
        ) from exc


def _count(rule: ModelValidatorRule, key: str) -> int:
    value = (rule.parameters or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _invalid(rule, f"parameter {key!r} must be an integer of at least 1")
    return value


def _flag(rule: ModelValidatorRule, key: str) -> bool:
    value = (rule.parameters or {}).get(key)
    if not isinstance(value, bool):
        raise _invalid(rule, f"parameter {key!r} must be true or false")
    return value


def _issue(
    rule: ModelValidatorRule, file_path: Path, subject: str, detail: str
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{subject}: {detail} -- {_text(rule, 'remediation', required=True)}",
        code=rule.rule_id,
        file_path=file_path,
        rule_name=rule.rule_id,
    )


def _validate_rule(rule: ModelValidatorRule) -> str:
    """Read every parameter of an enabled row once; return its kind."""
    kind = _text(rule, "kind", required=True)
    _text(rule, "reason", required=True)
    _text(rule, "remediation", required=True)
    if kind == "run_step_signal":
        shell = _pattern(rule, "shell_pattern", required=False)
        run = _pattern(rule, "run_pattern", required=False)
        if shell is None and run is None:
            raise _invalid(rule, "needs 'shell_pattern' or 'run_pattern'")
    elif kind == "run_block_length":
        _count(rule, "max_run_lines")
    elif kind == "check_value_program":
        _pattern(rule, "program_pattern", required=True)
        _count(rule, "max_inline_chars")
        _flag(rule, "refuse_newline")
    else:
        raise _invalid(rule, f"unknown kind {kind!r}")
    return kind


def _step_subject(step: ModelInlineLogicRunStep) -> str:
    return f"job {step.job} step {step.step}"


def _check_step(
    rule: ModelValidatorRule,
    kind: str,
    file_path: Path,
    step: ModelInlineLogicRunStep,
) -> ModelValidationIssue | None:
    reason = _text(rule, "reason", required=True)
    if kind == "run_step_signal":
        shell = _pattern(rule, "shell_pattern", required=False)
        run = _pattern(rule, "run_pattern", required=False)
        by_shell = (
            shell is not None and step.shell is not None and shell.search(step.shell)
        )
        by_run = run is not None and run.search(step.run)
        if by_shell or by_run:
            return _issue(rule, file_path, _step_subject(step), reason)
    elif kind == "run_block_length":
        lines = sum(1 for line in step.run.splitlines() if line.strip())
        limit = _count(rule, "max_run_lines")
        if lines > limit:
            return _issue(
                rule,
                file_path,
                _step_subject(step),
                f"{lines} lines, at most {limit} allowed ({reason})",
            )
    return None


def _check_value(
    rule: ModelValidatorRule,
    file_path: Path,
    value: ModelInlineLogicCheckValue,
) -> ModelValidationIssue | None:
    program = _pattern(rule, "program_pattern", required=True)
    if program is None or not program.search(value.check_value):
        return None
    body = value.check_value.strip()
    limit = _count(rule, "max_inline_chars")
    reasons: list[str] = []
    if len(body) > limit:
        reasons.append(f"{len(body)} characters, at most {limit} allowed")
    if _flag(rule, "refuse_newline") and "\n" in body:
        reasons.append("holds a newline")
    if not reasons:
        return None
    detail = ", ".join(reasons) + f" ({_text(rule, 'reason', required=True)})"
    return _issue(rule, file_path, f"check {value.evidence_ref}", detail)


def check_inline_logic(
    file_path: Path,
    run_steps: tuple[ModelInlineLogicRunStep, ...],
    check_values: tuple[ModelInlineLogicCheckValue, ...],
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per (run step or check value, enabled rule) that fires.

    Raises ``ModelOnexError`` when an enabled rule row carries an unreadable
    parameter, so an invalid contract fails to load instead of passing.
    """
    kinds = {rule.rule_id: _validate_rule(rule) for rule in rules if rule.enabled}
    enabled = [rule for rule in rules if rule.enabled]
    issues: list[ModelValidationIssue] = []
    for step in run_steps:
        for rule in enabled:
            found = _check_step(rule, kinds[rule.rule_id], file_path, step)
            if found is not None:
                issues.append(found)
    for value in check_values:
        for rule in enabled:
            if kinds[rule.rule_id] == "check_value_program":
                found = _check_value(rule, file_path, value)
                if found is not None:
                    issues.append(found)
    return tuple(issues)
