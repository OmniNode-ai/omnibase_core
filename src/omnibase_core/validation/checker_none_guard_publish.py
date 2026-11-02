# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``none_guard_publish`` (OMN-22005, replacing the OMN-10818 report-mode script).

``if event_bus is not None:`` (or the truthy ``if event_bus:``) around a publish call skips
the publication when the bus is absent, so an optional bus leaves silent gaps. Facts in (one
module's path and source), ``ModelValidationIssue`` out. The bus names, the publish method
names, the annotation marker (a comment prefix and a name) and the reason and remediation texts are ``parameters`` of the
``none_guard_publish`` rule row of ``contracts/none_guard_publish.validation.yaml``.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_NONE_GUARD_PUBLISH = "none_guard_publish"


def _is_bus_name(node: ast.expr, names: frozenset[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.Attribute):
        return node.attr in names
    return False


def _is_bus_none_guard(test: ast.expr, names: frozenset[str]) -> bool:
    if isinstance(test, ast.Compare):
        return (
            len(test.ops) == 1
            and isinstance(test.ops[0], ast.IsNot)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value is None
            and _is_bus_name(test.left, names)
        )
    if isinstance(test, (ast.Name, ast.Attribute)):
        return _is_bus_name(test, names)
    return False


def _has_publish_call(
    body: list[ast.stmt], names: frozenset[str], methods: frozenset[str]
) -> bool:
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
            and _is_bus_name(node.func.value, names)
        ):
            return True
    return False


def check_none_guard_publish(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``none_guard_publish`` row, ordered by line."""
    row = rules.get(RULE_NONE_GUARD_PUBLISH)
    if row is None or not row.enabled:
        return ()
    names = frozenset(rule_strings(row, "bus_names"))
    methods = frozenset(rule_strings(row, "publish_methods"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    issues = [
        detector_issue(row, path, lines, node.lineno, reason, remediation)
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and _is_bus_none_guard(node.test, names)
        and not is_annotated(lines, node.lineno, marker)
        and _has_publish_call(node.body, names, methods)
    ]
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_NONE_GUARD_PUBLISH", "check_none_guard_publish"]
