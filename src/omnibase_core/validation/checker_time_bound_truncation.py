# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``time_bound_truncation`` (OMN-23186).

A duration read cut to whole seconds (``int(td.total_seconds())``, ``math.floor(...)``, ``... // 1``) and
then compared to a limit moves the boundary by up to a second: a read a fraction of a second past a
deadline, or a fraction of a second in the future, passes the check. Facts in (one module's path and
source), ``ModelValidationIssue`` out. A truncation is a finding when its value, directly or through a
name assigned from it, reaches a comparison in the same function. The truncating calls and operators,
the duration methods, the annotation marker (a comment prefix and a name) and the reason and
remediation texts are ``parameters`` of the ``time_bound_truncation`` rule row of
``contracts/time_bound_truncation.validation.yaml``.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    dotted_name,
    is_annotated,
    parent_map,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_TIME_BOUND_TRUNCATION = "time_bound_truncation"


def _own_nodes(function: ast.AST) -> Iterator[ast.AST]:
    """Nodes of ``function``'s own scope: nested functions and classes are judged on their own."""
    pending = list(ast.iter_child_nodes(function))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            pending.extend(ast.iter_child_nodes(node))


def _is_duration_call(node: ast.AST, methods: frozenset[str]) -> bool:
    """The duration read itself (``td.total_seconds()``), not a scaled or derived value."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in methods
    )


def _is_truncation(
    node: ast.AST,
    calls: frozenset[str],
    operators: frozenset[str],
    methods: frozenset[str],
) -> bool:
    if isinstance(node, ast.Call):
        return dotted_name(node.func) in calls and any(
            _is_duration_call(arg, methods) for arg in node.args
        )
    if isinstance(node, ast.BinOp):
        return type(node.op).__name__ in operators and _is_duration_call(
            node.left, methods
        )
    return False


def _bound_names(node: ast.AST, parents: Mapping[ast.AST, ast.AST]) -> set[str]:
    """Names a truncation's value is assigned to, through arithmetic wrappers."""
    cursor = node
    while isinstance(parents.get(cursor), (ast.BinOp, ast.UnaryOp)):
        cursor = parents[cursor]
    parent = parents.get(cursor)
    if isinstance(parent, ast.Assign) and parent.value is cursor:
        return {t.id for t in parent.targets if isinstance(t, ast.Name)}
    if (
        isinstance(parent, (ast.AnnAssign, ast.NamedExpr))
        and isinstance(parent.target, ast.Name)
        and parent.value is cursor
    ):
        return {parent.target.id}
    return set()


def _directly_compared(node: ast.AST, parents: Mapping[ast.AST, ast.AST]) -> bool:
    cursor = node
    while isinstance(parents.get(cursor), (ast.BinOp, ast.UnaryOp)):
        cursor = parents[cursor]
    return isinstance(parents.get(cursor), ast.Compare)


def check_time_bound_truncation(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``time_bound_truncation`` row, ordered by line."""
    row = rules.get(RULE_TIME_BOUND_TRUNCATION)
    if row is None or not row.enabled:
        return ()
    calls = frozenset(rule_strings(row, "truncating_calls"))
    operators = frozenset(rule_strings(row, "truncating_operators"))
    methods = frozenset(rule_strings(row, "duration_methods"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    parents = parent_map(tree)
    issues: list[ModelValidationIssue] = []
    seen: set[int] = set()
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        scope = list(_own_nodes(function))
        compared = {
            n.id
            for cmp in scope
            if isinstance(cmp, ast.Compare)
            for operand in (cmp.left, *cmp.comparators)
            for n in ast.walk(operand)
            if isinstance(n, ast.Name)
        }
        for node in scope:
            if not _is_truncation(node, calls, operators, methods):
                continue
            lineno = getattr(node, "lineno", 0)
            reaches_bound = _directly_compared(node, parents) or bool(
                _bound_names(node, parents) & compared
            )
            if lineno in seen:
                continue
            if reaches_bound and not is_annotated(lines, lineno, marker):
                seen.add(lineno)
                issues.append(
                    detector_issue(row, path, lines, lineno, reason, remediation)
                )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_TIME_BOUND_TRUNCATION", "check_time_bound_truncation"]
