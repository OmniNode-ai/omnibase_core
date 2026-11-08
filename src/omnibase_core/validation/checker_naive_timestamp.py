# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``naive_timestamp`` (OMN-23186).

A request or reading model field typed ``datetime`` accepts a naive value, and a window compare against
an aware clock then raises; a ``strptime`` on a request field with no handler for ``ValueError``
aborts the whole batch on one malformed timestamp. Facts in (one module's path and source),
``ModelValidationIssue`` out.

Rows: ``naive_datetime_field`` (a field annotation naming a naive type in a class whose name matches
a model-class pattern; ``AwareDatetime`` is a different name and passes) and ``unguarded_strptime`` (a parse call whose
first argument reads an attribute of a request-named root, outside a ``try`` that catches one of the
guard exceptions). The class patterns, type names, method and root names, guard exceptions, annotation
markers and texts are ``parameters`` of the rows of ``contracts/naive_timestamp.validation.yaml``.
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
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
    parent_map,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_NAIVE_DATETIME_FIELD = "naive_datetime_field"
RULE_UNGUARDED_STRPTIME = "unguarded_strptime"


def _type_names(annotation: ast.expr) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _naive_fields(
    tree: ast.Module, lines: list[str], path: Path, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    classes = [re.compile(p) for p in rule_strings(row, "class_name_patterns")]
    naive = frozenset(rule_strings(row, "naive_types"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    issues: list[ModelValidationIssue] = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef) or not any(
            p.search(cls.name) for p in classes
        ):
            continue
        for stmt in cls.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            names = _type_names(stmt.annotation)
            if names & naive:
                if not is_annotated(lines, stmt.lineno, marker):
                    issues.append(
                        detector_issue(
                            row, path, lines, stmt.lineno, reason, remediation
                        )
                    )
    return issues


def _root_name(node: ast.expr) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _catches(handler: ast.ExceptHandler, guards: frozenset[str]) -> bool:
    if handler.type is None:
        return True
    elements = (
        handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    )
    return any(isinstance(e, ast.Name) and e.id in guards for e in elements)


def _guarded(
    call: ast.Call, parents: Mapping[ast.AST, ast.AST], guards: frozenset[str]
) -> bool:
    child: ast.AST = call
    parent = parents.get(child)
    while parent is not None:
        if (
            isinstance(parent, ast.Try)
            and child in parent.body
            and any(_catches(h, guards) for h in parent.handlers)
        ):
            return True
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return False
        child, parent = parent, parents.get(parent)
    return False


def _strptime_calls(
    tree: ast.Module, lines: list[str], path: Path, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    methods = frozenset(rule_strings(row, "parse_methods"))
    roots = frozenset(rule_strings(row, "request_roots"))
    guards = frozenset(rule_strings(row, "guard_exceptions"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    parents = parent_map(tree)
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
            and node.args
        ):
            continue
        reads_request = any(
            isinstance(n, ast.Attribute) and _root_name(n) in roots
            for n in ast.walk(node.args[0])
        )
        if (
            reads_request
            and not _guarded(node, parents, guards)
            and not is_annotated(lines, node.lineno, marker)
        ):
            issues.append(
                detector_issue(row, path, lines, node.lineno, reason, remediation)
            )
    return issues


def check_naive_timestamp(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``naive_timestamp`` rows, ordered by line."""
    tree = parse_module(source)
    lines = source.splitlines()
    issues: list[ModelValidationIssue] = []
    field_row = rules.get(RULE_NAIVE_DATETIME_FIELD)
    if field_row is not None and field_row.enabled:
        issues += _naive_fields(
            tree or ast.Module(body=[], type_ignores=[]), lines, path, field_row
        )
    parse_row = rules.get(RULE_UNGUARDED_STRPTIME)
    if parse_row is not None and parse_row.enabled:
        issues += _strptime_calls(
            tree or ast.Module(body=[], type_ignores=[]), lines, path, parse_row
        )
    return tuple(sorted(issues, key=lambda i: (i.line_number or 0, i.rule_name or "")))


__all__ = [
    "RULE_NAIVE_DATETIME_FIELD",
    "RULE_UNGUARDED_STRPTIME",
    "check_naive_timestamp",
]
