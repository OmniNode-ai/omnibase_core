# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure protocol-binding checker: facts in, ``ModelValidationIssue`` out (OMN-21533, K5).

A protocol is bound to its implementation in a binding site (a container
registration, an overlay), never in code that merely needs the protocol. This
module judges parsed Python source and parsed node contracts against the rule rows
of ``contracts/protocol_binding.validation.yaml``. The binding sites, the default
implementation classes, the implementation classes, the client classes, the key
pattern, the contract sections, the thresholds and the remediation texts are all
``parameters`` entries of a rule row; nothing here names a class, a protocol or a
path. The module performs no I/O: no file read, no clock, no environment.

Rule row kinds (the ``kind`` parameter):

* ``construction`` -- a call of one of ``classes`` outside ``binding_sites``.
* ``isinstance_branch`` -- ``isinstance(x, C)`` with ``C`` in ``classes``, outside
  ``binding_sites``.
* ``binding_table`` -- a module-level dict literal with a key matching ``key_pattern`` whose
  value does not name an import path (``reexport_value_pattern``: a lazy re-export table).
* ``setting_homes`` -- a literal setting of a contract ``sections`` mapping that
  another contract already holds (``min_homes`` contracts make an issue).

A ``construction`` row may carry a ``stale_message``: it then holds a file to a per-file
baseline (a path -> count mapping the caller supplies) of the findings that existed
before the rule, and a baseline entry above what the file holds is an issue.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = [
    "check_protocol_binding",
    "check_setting_two_homes",
    "contract_setting_keys",
    "parse_baseline",
]


def _kind(rule: ModelValidatorRule) -> str:
    return rule_string(rule, "kind")


def _pattern(rule: ModelValidatorRule, key: str) -> re.Pattern[str]:
    try:
        return re.compile(rule_string(rule, key))
    except re.error as exc:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: parameter {key!r} is not a regular expression: {exc}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        ) from exc


def _validate_row(rule: ModelValidatorRule) -> None:
    """Read every parameter of an enabled row so a broken contract raises, never passes."""
    kind = _kind(rule)
    rule_string(rule, "remediation")
    if kind in {"construction", "isinstance_branch"}:
        rule_strings(rule, "classes")
        rule_strings(rule, "binding_sites")
    elif kind == "binding_table":
        _pattern(rule, "key_pattern")
        _pattern(rule, "reexport_value_pattern")
    elif kind == "setting_homes":
        rule_strings(rule, "sections")
        if rule_int(rule, "min_homes") < 2:
            raise ModelOnexError(
                message=f"rule {rule.rule_id!r}: parameters.min_homes must be at least 2",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
    else:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: unknown kind {kind!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    if kind == "construction" and "stale_message" in (rule.parameters or {}):
        rule_string(rule, "stale_message")


def _issue(
    rule: ModelValidatorRule, path: Path, detail: str, line: int | None
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{detail} -- {rule_string(rule, 'remediation')}",
        code=rule.rule_id,
        file_path=path,
        line_number=line,
        rule_name=rule.rule_id,
    )


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _class_names(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.Tuple):
        return [name for element in node.elts for name in _class_names(element)]
    return []


def _at_binding_site(path: Path, rule: ModelValidatorRule) -> bool:
    posix = path.as_posix()
    return any(fnmatch(posix, glob) for glob in rule_strings(rule, "binding_sites"))


def _table_entries(node: ast.stmt) -> list[tuple[str, ast.expr]]:
    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
    if not isinstance(value, ast.Dict):
        return []
    return [
        (key.value, entry)
        for key, entry in zip(value.keys, value.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    ]


def _names_import_path(entry: ast.expr, reexport: re.Pattern[str]) -> bool:
    return any(
        isinstance(part, ast.Constant)
        and isinstance(part.value, str)
        and reexport.search(part.value)
        for part in ast.walk(entry)
    )


def _check_construction(
    rule: ModelValidatorRule, path: Path, tree: ast.Module
) -> list[ModelValidationIssue]:
    if _at_binding_site(path, rule):
        return []
    classes = set(rule_strings(rule, "classes"))
    return [
        _issue(
            rule,
            path,
            f"{_called_name(node)} is constructed outside a binding site",
            node.lineno,
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _called_name(node) in classes
    ]


def _check_isinstance(
    rule: ModelValidatorRule, path: Path, tree: ast.Module
) -> list[ModelValidationIssue]:
    if _at_binding_site(path, rule):
        return []
    classes = set(rule_strings(rule, "classes"))
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and _called_name(node) == "isinstance"
            and len(node.args) == 2
        ):
            hit = classes.intersection(_class_names(node.args[1]))
            if hit:
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"isinstance branches on the implementation {sorted(hit)[0]}",
                        node.lineno,
                    )
                )
    return issues


def _check_binding_table(
    rule: ModelValidatorRule, path: Path, tree: ast.Module
) -> list[ModelValidationIssue]:
    pattern = _pattern(rule, "key_pattern")
    reexport = _pattern(rule, "reexport_value_pattern")
    issues: list[ModelValidationIssue] = []
    for node in tree.body:
        for key, entry in _table_entries(node):
            if pattern.search(key) and not _names_import_path(entry, reexport):
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"module-level table binds {key!r} in code",
                        node.lineno,
                    )
                )
                break
    return issues


def _apply_baseline(
    rule: ModelValidatorRule,
    path: Path,
    issues: list[ModelValidationIssue],
    baselined: int,
) -> list[ModelValidationIssue]:
    """A file may hold no more findings than its entry, and no fewer unrecorded."""
    if "stale_message" not in (rule.parameters or {}):
        return issues
    values = {"path": path.as_posix(), "count": len(issues), "baselined": baselined}
    if len(issues) > baselined:
        return issues
    if len(issues) < baselined:
        return [
            _issue(
                rule, path, rule_string(rule, "stale_message").format(**values), None
            )
        ]
    return []


def check_protocol_binding(
    path: Path,
    source: str,
    rules: Sequence[ModelValidatorRule],
    baseline: Mapping[str, int] | None = None,
) -> tuple[ModelValidationIssue, ...]:
    """Issues of one Python source, in rule order then line order.

    ``baseline`` maps a path (as ``path.as_posix()``) to the number of findings of
    the baselined rule that the file held before the rule existed. Raises
    ``ModelOnexError`` for an enabled rule row with an unreadable parameter, and for
    source that does not parse, so neither passes.
    """
    enabled = [rule for rule in rules if rule.enabled]
    for rule in enabled:
        _validate_row(rule)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ModelOnexError(
            message=f"{path}: source does not parse: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    issues: list[ModelValidationIssue] = []
    for rule in enabled:
        kind = _kind(rule)
        found: list[ModelValidationIssue] = []
        if kind == "construction":
            found = _apply_baseline(
                rule,
                path,
                _check_construction(rule, path, tree),
                (baseline or {}).get(path.as_posix(), 0),
            )
        elif kind == "isinstance_branch":
            found = _check_isinstance(rule, path, tree)
        elif kind == "binding_table":
            found = _check_binding_table(rule, path, tree)
        issues.extend(found)
    return tuple(sorted(issues, key=lambda i: (i.line_number or 0, i.code or "")))


def parse_baseline(text: str | None) -> dict[str, int]:
    """Path -> findings, from ``<path> <count>`` lines; ``#`` lines are prose."""
    entries: dict[str, int] = {}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path, _, count = stripped.rpartition(" ")
        if path and count.isdigit():
            entries[path] = int(count)
    return entries


def _literal_keys(node: object, keys: list[str]) -> None:
    if not isinstance(node, Mapping):
        return
    for key, value in node.items():
        if isinstance(value, Mapping):
            _literal_keys(value, keys)
        elif isinstance(value, (str, int, float, bool)) and isinstance(key, str):
            keys.append(key)


def contract_setting_keys(
    document: Mapping[str, object], rules: Sequence[ModelValidatorRule]
) -> tuple[str, ...]:
    """The setting keys one contract holds a literal value for, in the rows' sections."""
    keys: list[str] = []
    for rule in rules:
        if rule.enabled and _kind(rule) == "setting_homes":
            for section in rule_strings(rule, "sections"):
                _literal_keys(document.get(section), keys)
    return tuple(dict.fromkeys(keys))


def check_setting_two_homes(
    path: Path,
    keys: Sequence[str],
    homes: Mapping[str, Sequence[str]],
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per setting key that ``min_homes`` contracts now hold a literal for.

    ``homes`` maps a key to the contracts already read that hold it.
    """
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        _validate_row(rule)
        if _kind(rule) != "setting_homes":
            continue
        floor = rule_int(rule, "min_homes")
        for key in keys:
            earlier = [h for h in homes.get(key, ()) if h != path.as_posix()]
            if len(earlier) + 1 >= floor:
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"setting {key!r} holds a literal here and in {', '.join(earlier)}",
                        None,
                    )
                )
    return tuple(issues)
