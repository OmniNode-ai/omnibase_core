# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for K10 ``checker_rule_data`` (OMN-21503).

No path or pattern is a literal in a checker: every rule table lives in the
checker's ``.validation.yaml``. Facts in (one module's source, its name, the
names beside it), ``ModelValidationIssue`` out: no file read, no clock, no
environment. Every name, marker and pattern is a ``parameters`` entry of the
matching rule row in ``contracts/checker_rule_data.validation.yaml``.

Rules: rule_table_in_checker, validator_outside_generic_format, rule_table_baseline.

``validator_outside_generic_format`` refuses a NEW validator: when the entry names a base
revision, a module that revision already holds is migrated by deleting it, not refused
on every edit; with no base revision every module is refused.

``rule_table_baseline`` is the shrink-only ratchet over the rule tables that sat in
checkers before K10 existed: the baseline file maps a path to the number of tables it
holds, a file may not hold more than its entry, an entry must equal what the file holds,
and an entry the base revision does not have (or has lower) fails.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_checker_rule_data_module_fact import (
    ModelCheckerRuleDataModuleFact,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

RULE_TABLE = "rule_table_in_checker"
RULE_FORMAT = "validator_outside_generic_format"
RULE_BASELINE = "rule_table_baseline"


def _issue(
    rule: ModelValidatorRule, path: Path, message: str, line: int | None = None
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=message,
        code=rule.rule_id,
        file_path=path,
        line_number=line,
        rule_name=rule.rule_id,
    )


def _active(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> bool:
    row = rules.get(rule_id)
    return row is not None and row.enabled


def _parse(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _returns_any(tree: ast.Module, names: tuple[str, ...]) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.returns:
            annotation = ast.unparse(node.returns)
            if any(re.search(rf"\b{re.escape(n)}\b", annotation) for n in names):
                return True
    return False


def _subclasses_any(tree: ast.Module, names: tuple[str, ...]) -> bool:
    return any(
        isinstance(node, ast.ClassDef)
        and any(ast.unparse(base).split(".")[-1] in names for base in node.bases)
        for node in ast.walk(tree)
    )


def _is_checker_module(
    fact: ModelCheckerRuleDataModuleFact, tree: ast.Module, row: ModelValidatorRule
) -> bool:
    if fact.name.startswith(rule_strings(row, "qualifying_name_prefixes")):
        return True
    if any(
        re.search(p, fact.posix_path)
        for p in rule_strings(row, "qualifying_path_patterns")
    ):
        return True
    if _subclasses_any(tree, rule_strings(row, "qualifying_base_names")):
        return True
    if _returns_any(tree, rule_strings(row, "qualifying_return_names")):
        return True
    return bool(
        re.search(rule_string(row, "cli_gate_name_pattern"), fact.name)
    ) and any(m in fact.source for m in rule_strings(row, "writer_markers"))


def _rule_table_kind(value: ast.expr, row: ModelValidatorRule) -> str | None:
    if isinstance(value, ast.Call):
        callee = ast.unparse(value.func)
        if callee in rule_strings(row, "collection_calls") and (
            value.args or value.keywords
        ):
            return callee
        return None
    if isinstance(value, ast.Set | ast.Tuple) and value.elts:
        return type(value).__name__.lower()
    if isinstance(value, ast.Dict) and value.keys:
        return "dict"
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        if len(value.value.split()) >= rule_int(row, "min_string_words"):
            return "multi-word string"
    return None


def _check_rule_table(
    path: Path,
    fact: ModelCheckerRuleDataModuleFact,
    tree: ast.Module,
    row: ModelValidatorRule,
) -> list[ModelValidationIssue]:
    if not _is_checker_module(fact, tree, row):
        return []
    constant = re.compile(rule_string(row, "constant_name_pattern"))
    issues: list[ModelValidationIssue] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        kind = _rule_table_kind(value, row)
        if kind is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and constant.match(target.id):
                issues.append(
                    _issue(
                        row,
                        path,
                        f"{target.id} is a {kind} constant in a checker: {row.description}",
                        node.lineno,
                    )
                )
    return issues


def _check_generic_format(
    path: Path,
    fact: ModelCheckerRuleDataModuleFact,
    tree: ast.Module,
    row: ModelValidatorRule,
) -> list[ModelValidationIssue]:
    report_markers = rule_strings(row, "report_markers")
    if re.search(rule_string(row, "one_off_name_pattern"), fact.name):
        own_main = any(m in fact.source for m in rule_strings(row, "one_off_markers"))
        own_writer = any(m in fact.source for m in rule_strings(row, "writer_markers"))
        if own_writer or (own_main and any(m in fact.source for m in report_markers)):
            return [
                _issue(
                    row,
                    path,
                    f"{fact.name} is a one-off validator CLI: {row.description}",
                )
            ]
    if not _returns_any(tree, rule_strings(row, "report_return_names")):
        return []
    prefixes = (
        rule_string(row, "checker_prefix"),
        rule_string(row, "validator_prefix"),
    )
    for own, other in (prefixes, prefixes[::-1]):
        if fact.name.startswith(own):
            validator_id = fact.name[len(own) :].removesuffix(".py")
            has_triple = (
                f"{other}{validator_id}.py" in fact.sibling_names
                and f"{validator_id}{rule_string(row, 'contract_suffix')}"
                in fact.contract_names
            )
            if has_triple:
                return []
            break
    return [
        _issue(
            row,
            path,
            f"{fact.name} returns a validation report outside the generic format: "
            f"{row.description}",
        )
    ]


def check_module(
    path: Path,
    fact: ModelCheckerRuleDataModuleFact,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the enabled K10 rules."""
    tree = _parse(fact.source)
    if tree is None:
        return ()
    issues: list[ModelValidationIssue] = []
    if _active(rules, RULE_TABLE):
        issues.extend(_check_rule_table(path, fact, tree, rules[RULE_TABLE]))
    if _active(rules, RULE_FORMAT) and fact.new_in_change:
        issues.extend(_check_generic_format(path, fact, tree, rules[RULE_FORMAT]))
    return tuple(issues)


def parse_baseline(text: str | None) -> dict[str, int]:
    """Path -> number of rule tables, from ``<path> <count>`` lines; ``#`` lines are prose."""
    entries: dict[str, int] = {}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path, _, count = stripped.rpartition(" ")
        if path and count.isdigit():
            entries[path] = int(count)
    return entries


def apply_baseline(
    path: Path,
    issues: tuple[ModelValidationIssue, ...],
    baselined: int,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Hold a file to its baseline entry: no more tables than baselined, and none fewer unrecorded."""
    if not _active(rules, RULE_BASELINE):
        return issues
    row = rules[RULE_BASELINE]
    tables = [i for i in issues if i.code == RULE_TABLE]
    others = tuple(i for i in issues if i.code != RULE_TABLE)
    values = {"path": path.as_posix(), "count": len(tables), "baselined": baselined}
    if len(tables) > baselined:
        grown = (
            (_issue(row, path, rule_string(row, "grew_message").format(**values)),)
            if baselined
            else ()
        )
        return (*issues, *grown)
    if len(tables) < baselined:
        stale = _issue(row, path, rule_string(row, "stale_message").format(**values))
        return (*others, stale)
    return others


def baseline_growth(
    head: Mapping[str, int],
    base: Mapping[str, int],
    baseline_path: Path,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """An entry the base revision lacks, or holds at a lower count, is a baseline that grew."""
    if not _active(rules, RULE_BASELINE):
        return ()
    row = rules[RULE_BASELINE]
    return tuple(
        _issue(
            row,
            baseline_path,
            rule_string(row, "growth_message").format(
                path=path, count=count, baselined=base.get(path, 0)
            ),
        )
        for path, count in sorted(head.items())
        if count > base.get(path, 0)
    )


__all__ = [
    "RULE_BASELINE",
    "RULE_FORMAT",
    "RULE_TABLE",
    "ModelCheckerRuleDataModuleFact",
    "apply_baseline",
    "baseline_growth",
    "check_module",
    "parse_baseline",
]
