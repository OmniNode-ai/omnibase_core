# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure fail-loud checker: facts in, ``ModelValidationIssue`` out (OMN-22357).

A pre-commit hook must fail loud: a gate that cannot run, or that fails, must not
exit zero. This module judges parsed hooks, and the gate scripts their entries
invoke, against the rule rows of ``contracts/precommit_fail_loud.validation.yaml``.
Every pattern, window, script scope, stage name and remediation text is a
``parameters`` entry of a rule row; nothing here names a hook, a tool or a
repository. The module performs no I/O: the validator reads the referenced scripts
and passes their text in.

Rule row kinds (the ``kind`` parameter):

* ``hook_count_floor`` -- a file with fewer than ``min_hooks`` hooks is an issue, so
  a scan that reads nothing is never a pass.
* ``line_signal`` -- ``pattern`` is searched line by line in each scanned hook's
  command text (and, when ``read_scripts`` is true, in the scripts it
  invokes); ``unless`` (optional) clears a line.
* ``windowed_exit`` -- a line matching ``exit_pattern`` is an issue when a line of
  the ``window`` lines up to and including it matches ``signal_pattern`` and, when
  ``guard_pattern`` is given, a line of the same window matches it too.
* ``stage_coverage`` -- every stage a hook uses must be installed by the config's
  ``default_install_hook_types`` (``default_when_absent`` when it names none),
  except the ``allowed_uninstalled`` stages; judged on a config file only.
* ``script_reference`` -- carries no finding; names how an entry token resolves to a
  script (``prefixes``, ``suffixes``) for the rows that read scripts.

A line carrying a rule row's ``suppression_marker`` is skipped by that row.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.precommit_fail_loud.model_fail_loud_document import (
    ModelFailLoudDocument,
)
from omnibase_core.models.precommit_fail_loud.model_fail_loud_hook import (
    ModelFailLoudHook,
)

__all__ = ["check_precommit_fail_loud", "referenced_scripts"]

_KIND_SCRIPT_REFERENCE = "script_reference"
_SHOWN_LINE_WIDTH = 120


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"precommit_fail_loud rule {rule.rule_id!r}: {detail}",
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


def _texts(rule: ModelValidatorRule, key: str, *, required: bool) -> tuple[str, ...]:
    value = (rule.parameters or {}).get(key)
    if value is None:
        if required:
            raise _invalid(rule, f"parameter {key!r} is required")
        return ()
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise _invalid(rule, f"parameter {key!r} must be a list of non-empty strings")
    if required and not value:
        raise _invalid(rule, f"parameter {key!r} must not be empty")
    return tuple(value)


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


def _whole(rule: ModelValidatorRule, key: str) -> int:
    value = (rule.parameters or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _invalid(rule, f"parameter {key!r} must be an integer of at least 1")
    return value


def _reads_scripts(rule: ModelValidatorRule) -> bool:
    value = (rule.parameters or {}).get("read_scripts")
    if not isinstance(value, bool):
        raise _invalid(rule, "parameter 'read_scripts' must be true or false")
    return value


def _issue(
    rule: ModelValidatorRule, file_path: Path, detail: str
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{detail} -- {_text(rule, 'remediation', required=True)}",
        code=rule.rule_id,
        file_path=file_path,
        rule_name=rule.rule_id,
    )


def _scanned(
    hooks: Sequence[ModelFailLoudHook], languages: Sequence[str]
) -> list[ModelFailLoudHook]:
    return [
        hook for hook in hooks if hook.entry is not None and hook.language in languages
    ]


def _script_rule(rules: Sequence[ModelValidatorRule]) -> ModelValidatorRule | None:
    for rule in rules:
        if (
            rule.enabled
            and _text(rule, "kind", required=True) == _KIND_SCRIPT_REFERENCE
        ):
            return rule
    return None


def _tokens(hook: ModelFailLoudHook, rule: ModelValidatorRule) -> list[str]:
    prefixes = _texts(rule, "prefixes", required=True)
    suffixes = _texts(rule, "suffixes", required=True)
    return [
        token
        for token in " ".join(hook.command_lines).replace("\n", " ").split()
        if token.endswith(suffixes) and token.startswith(prefixes)
    ]


def referenced_scripts(
    document: ModelFailLoudDocument, rules: Sequence[ModelValidatorRule]
) -> tuple[str, ...]:
    """Every entry token that may name a script, in hook order, without repeats.

    The validator reads the ones that exist and hands their text to
    ``check_precommit_fail_loud``.
    """
    rule = _script_rule(rules)
    if rule is None:
        return ()
    found: dict[str, None] = {}
    for hook in _scanned(document.hooks, _texts(rule, "languages", required=True)):
        for token in _tokens(hook, rule):
            found[token] = None
    return tuple(found)


def _blocks(
    document: ModelFailLoudDocument,
    scripts: Mapping[str, str],
    rules: Sequence[ModelValidatorRule],
    rule: ModelValidatorRule,
) -> list[tuple[str, str]]:
    """The (label, text) blocks one rule row scans: entries, then each script once."""
    blocks: list[tuple[str, str]] = []
    seen: set[str] = set()
    script_rule = _script_rule(rules) if _reads_scripts(rule) else None
    for hook in _scanned(document.hooks, _texts(rule, "languages", required=True)):
        blocks.append((f"hook {hook.id} entry", "\n".join(hook.command_lines)))
        if script_rule is None:
            continue
        for token in _tokens(hook, script_rule):
            if token in scripts:
                if token not in seen:
                    seen.add(token)
                    blocks.append((f"script {token}", scripts[token]))
                break
    return blocks


def _shown(line: str) -> str:
    return line.strip()[:_SHOWN_LINE_WIDTH]


def _check_line_signal(
    rule: ModelValidatorRule, file_path: Path, blocks: list[tuple[str, str]]
) -> list[ModelValidationIssue]:
    pattern = _pattern(rule, "pattern", required=True)
    unless = _pattern(rule, "unless", required=False)
    marker = _text(rule, "suppression_marker", required=False)
    reason = _text(rule, "reason", required=True)
    issues: list[ModelValidationIssue] = []
    for label, text in blocks:
        for number, line in enumerate(text.splitlines(), start=1):
            if marker and marker in line:
                continue
            if pattern is not None and pattern.search(line):
                if unless is not None and unless.search(line):
                    continue
                issues.append(
                    _issue(
                        rule,
                        file_path,
                        f"{label}:{number}: {reason} [{_shown(line)}]",
                    )
                )
    return issues


def _check_windowed_exit(
    rule: ModelValidatorRule, file_path: Path, blocks: list[tuple[str, str]]
) -> list[ModelValidationIssue]:
    exit_pattern = _pattern(rule, "exit_pattern", required=True)
    signal = _pattern(rule, "signal_pattern", required=True)
    guard = _pattern(rule, "guard_pattern", required=False)
    width = _whole(rule, "window")
    marker = _text(rule, "suppression_marker", required=False)
    reason = _text(rule, "reason", required=True)
    issues: list[ModelValidationIssue] = []
    for label, text in blocks:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if exit_pattern is None or signal is None:
                continue
            if not exit_pattern.search(line) or (marker and marker in line):
                continue
            window = lines[max(0, index - width) : index + 1]
            signalled = any(
                signal.search(seen) and not (marker and marker in seen)
                for seen in window
            )
            guarded = guard is None or any(guard.search(seen) for seen in window)
            if signalled and guarded:
                issues.append(
                    _issue(
                        rule,
                        file_path,
                        f"{label}:{index + 1}: {reason} [{_shown(line)}]",
                    )
                )
    return issues


def _check_stage_coverage(
    rule: ModelValidatorRule, file_path: Path, document: ModelFailLoudDocument
) -> list[ModelValidationIssue]:
    allowed = set(_texts(rule, "allowed_uninstalled", required=False))
    default = _texts(rule, "default_when_absent", required=True)
    _text(rule, "reason", required=True)
    if not document.is_config:
        return []
    installed = set(
        default if document.installed_stages is None else document.installed_stages
    )
    used = {stage for hook in document.hooks for stage in hook.stages}
    uncovered = sorted(used - installed - allowed)
    if not uncovered:
        return []
    return [
        _issue(
            rule,
            file_path,
            f"default_install_hook_types={sorted(installed)} does not cover "
            f"stage(s) {uncovered} used by one or more hooks "
            f"({_text(rule, 'reason', required=True)})",
        )
    ]


def check_precommit_fail_loud(
    file_path: Path,
    document: ModelFailLoudDocument,
    scripts: Mapping[str, str],
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per finding of each enabled rule, in rule order then file order.

    ``scripts`` maps an entry token from ``referenced_scripts`` to the text of the
    script it names; a token with no entry is not a file and is not scanned.
    Raises ``ModelOnexError`` when an enabled rule row carries an unreadable
    parameter, so an invalid contract fails to load instead of passing.
    """
    issues: list[ModelValidationIssue] = []
    for rule in (rule for rule in rules if rule.enabled):
        kind = _text(rule, "kind", required=True)
        if kind != _KIND_SCRIPT_REFERENCE:
            _text(rule, "remediation", required=True)
        if kind == "hook_count_floor":
            floor = _whole(rule, "min_hooks")
            _text(rule, "reason", required=True)
            if len(document.hooks) < floor:
                issues.append(
                    _issue(
                        rule,
                        file_path,
                        f"{len(document.hooks)} hook(s) read, at least {floor} "
                        f"expected ({_text(rule, 'reason', required=True)})",
                    )
                )
        elif kind == "line_signal":
            issues.extend(
                _check_line_signal(
                    rule, file_path, _blocks(document, scripts, rules, rule)
                )
            )
        elif kind == "windowed_exit":
            issues.extend(
                _check_windowed_exit(
                    rule, file_path, _blocks(document, scripts, rules, rule)
                )
            )
        elif kind == "stage_coverage":
            issues.extend(_check_stage_coverage(rule, file_path, document))
        elif kind == _KIND_SCRIPT_REFERENCE:
            _texts(rule, "languages", required=True)
            _texts(rule, "prefixes", required=True)
            _texts(rule, "suffixes", required=True)
        else:
            raise _invalid(rule, f"unknown kind {kind!r}")
    return tuple(issues)
