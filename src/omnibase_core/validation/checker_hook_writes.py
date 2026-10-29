# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure hook-writes checker: facts in, ``ModelValidationIssue`` out (OMN-21498, T2.6).

A pre-commit hook checks and refuses; it never rewrites the files it was given.
This module judges parsed hooks against rule rows of
``contracts/hook_writes.validation.yaml``. Every pattern, hook id, argument list,
count floor and remediation text is a ``parameters`` entry of a rule row; nothing
here names a tool. The module performs no I/O: no file read, no clock, no
environment.

Rule row kinds (the ``kind`` parameter):

* ``command_signal`` -- ``pattern`` is searched in the hook's command text (its
  ``entry`` followed by its ``args``); ``unless`` (optional) clears the signal.
* ``rewriting_hook_id`` -- ``hook_id`` names a hook that rewrites by design; it is
  an issue unless one of ``check_only_args`` is a whole argument or entry token.
* ``hook_count_floor`` -- a hook file with fewer than ``min_hooks`` hooks is an
  issue, so a scan that reads nothing is never a pass.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.hook_writes.model_hook_writes_hook import ModelHookWritesHook

__all__ = ["check_hook_writes"]


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"hook_writes rule {rule.rule_id!r}: {detail}",
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


def _check_only_args(rule: ModelValidatorRule) -> list[str]:
    value = (rule.parameters or {}).get("check_only_args", [])
    if not isinstance(value, list):
        raise _invalid(rule, "parameter 'check_only_args' must be a list of strings")
    return value


def _tokens(hook: ModelHookWritesHook) -> list[str]:
    entry = hook.entry if hook.entry is not None else ""
    try:
        return shlex.split(entry)
    except ValueError:
        return entry.split()


def _issue(
    rule: ModelValidatorRule, file_path: Path, detail: str, hook_id: str | None
) -> ModelValidationIssue:
    subject = f"hook {hook_id}" if hook_id is not None else file_path.name
    return ModelValidationIssue(
        severity=rule.severity,
        message=(f"{subject}: {detail} -- {_text(rule, 'remediation', required=True)}"),
        code=rule.rule_id,
        file_path=file_path,
        rule_name=rule.rule_id,
    )


def check_hook_writes(
    file_path: Path,
    hooks: tuple[ModelHookWritesHook, ...],
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per (hook, enabled rule) that fires, in hook order then rule order.

    Raises ``ModelOnexError`` when an enabled rule row carries an unreadable
    parameter, so an invalid contract fails to load instead of passing.
    """
    issues: list[ModelValidationIssue] = []
    enabled = [rule for rule in rules if rule.enabled]
    for rule in enabled:
        kind = _text(rule, "kind", required=True)
        if kind == "hook_count_floor":
            floor = (rule.parameters or {}).get("min_hooks")
            if isinstance(floor, bool) or not isinstance(floor, int) or floor < 1:
                raise _invalid(
                    rule, "parameter 'min_hooks' must be an integer of at least 1"
                )
            if len(hooks) < floor:
                issues.append(
                    _issue(
                        rule,
                        file_path,
                        f"{len(hooks)} hook(s) read, at least {floor} expected "
                        f"({_text(rule, 'reason', required=True)})",
                        None,
                    )
                )
        elif kind == "command_signal":
            _pattern(rule, "pattern", required=True)
            _pattern(rule, "unless", required=False)
            _text(rule, "reason", required=True)
        elif kind == "rewriting_hook_id":
            _text(rule, "hook_id", required=True)
            _text(rule, "reason", required=True)
            _check_only_args(rule)
        else:
            raise _invalid(rule, f"unknown kind {kind!r}")

    for hook in hooks:
        command = hook.command
        for rule in enabled:
            kind = _text(rule, "kind", required=True)
            if kind == "command_signal":
                pattern = _pattern(rule, "pattern", required=True)
                unless = _pattern(rule, "unless", required=False)
                if (
                    pattern is not None
                    and pattern.search(command)
                    and not (unless is not None and unless.search(command))
                ):
                    issues.append(
                        _issue(
                            rule,
                            file_path,
                            f"the hook rewrites files ({_text(rule, 'reason', required=True)})",
                            hook.id,
                        )
                    )
            elif kind == "rewriting_hook_id" and hook.id == _text(
                rule, "hook_id", required=True
            ):
                tokens = _tokens(hook)
                if not any(
                    arg in hook.args or arg in tokens for arg in _check_only_args(rule)
                ):
                    issues.append(
                        _issue(
                            rule,
                            file_path,
                            f"the hook id rewrites files ({_text(rule, 'reason', required=True)})",
                            hook.id,
                        )
                    )
    return tuple(issues)
