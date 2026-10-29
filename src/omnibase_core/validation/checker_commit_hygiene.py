# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure commit-hygiene checker: facts in, ``ModelValidationIssue`` out (OMN-21498, K8).

Four refusals, none of which writes: a file without its final newline, a file with
more than one, a staged path that must stay out of the commit, and a line of a
commit message that must not be there. The module judges one file's relative path
and bytes against the rule rows of ``contracts/commit_hygiene.validation.yaml``;
every pattern and remediation text is a ``parameters`` entry of a rule row. It
performs no I/O: no file read, no clock, no environment.

Rule row kinds (the ``kind`` parameter), each with ``path_pattern`` (the rule
applies to a path it matches), optional ``exclude_path_pattern`` and
``remediation``:

* ``final_newline_missing`` -- non-empty content whose last byte is not a newline
  (content holding a NUL byte is binary and is not judged by either newline kind).
* ``final_newline_extra`` -- content that ends in more than one newline.
* ``path_refused`` -- the path itself is refused.
* ``content_line_refused`` -- a line matching ``line_pattern`` is refused.
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

__all__ = ["check_commit_hygiene"]

_NEWLINE = b"\n"
_BINARY_MARK = b"\x00"


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"commit_hygiene rule {rule.rule_id!r}: {detail}",
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


def _applies(rule: ModelValidatorRule, relative_path: str) -> bool:
    only = _pattern(rule, "path_pattern", required=True)
    skip = _pattern(rule, "exclude_path_pattern", required=False)
    return (
        only is not None
        and only.search(relative_path) is not None
        and not (skip is not None and skip.search(relative_path))
    )


def _issue(
    rule: ModelValidatorRule,
    file_path: Path,
    detail: str,
    line_number: int | None = None,
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{detail} -- {_text(rule, 'remediation', required=True)}",
        code=rule.rule_id,
        file_path=file_path,
        line_number=line_number,
        rule_name=rule.rule_id,
    )


def check_commit_hygiene(
    file_path: Path,
    relative_path: str,
    content: bytes,
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per enabled rule that fires on this file, in rule order.

    Raises ``ModelOnexError`` when an enabled rule row carries an unreadable
    parameter, so an invalid contract fails to load instead of passing.
    """
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        kind = _text(rule, "kind", required=True)
        if kind not in {
            "final_newline_missing",
            "final_newline_extra",
            "path_refused",
            "content_line_refused",
        }:
            raise _invalid(rule, f"unknown kind {kind!r}")
        _text(rule, "remediation", required=True)
        line_pattern = (
            _pattern(rule, "line_pattern", required=True)
            if kind == "content_line_refused"
            else None
        )
        if not _applies(rule, relative_path):
            continue
        if kind.startswith("final_newline") and _BINARY_MARK in content:
            continue
        if kind == "final_newline_missing":
            if content and not content.endswith(_NEWLINE):
                issues.append(
                    _issue(rule, file_path, "the file does not end in a newline")
                )
        elif kind == "final_newline_extra":
            if content.endswith(_NEWLINE * 2):
                issues.append(
                    _issue(rule, file_path, "the file ends in more than one newline")
                )
        elif kind == "path_refused":
            issues.append(_issue(rule, file_path, f"{relative_path} is refused"))
        elif line_pattern is not None:
            text = content.decode("utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                if line_pattern.search(line):
                    issues.append(
                        _issue(rule, file_path, f"line {number} is refused", number)
                    )
    return tuple(issues)
