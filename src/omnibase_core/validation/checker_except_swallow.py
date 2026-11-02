# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``except_swallow`` (OMN-22005, replacing the OMN-10817 report-mode script).

A broad ``except`` that logs and does not re-raise lets the caller carry on as if nothing
failed. Facts in (one module's path and source), ``ModelValidationIssue`` out. The broad
exception names, the logger method names, the annotation marker (a comment prefix and a name) and the reason and
remediation texts are ``parameters`` of the ``except_swallow`` rule row of
``contracts/except_swallow.validation.yaml``; an enabled row with a missing or mistyped
parameter raises, so a broken contract fails to load instead of passing every file.
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

RULE_EXCEPT_SWALLOW = "except_swallow"


def _catches_broad(handler: ast.ExceptHandler, broad: frozenset[str]) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name):
        return handler.type.id in broad
    if isinstance(handler.type, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in broad for e in handler.type.elts)
    return False


def _walk_body(body: list[ast.stmt]) -> list[ast.AST]:
    return list(ast.walk(ast.Module(body=body, type_ignores=[])))


def check_except_swallow(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``except_swallow`` row, ordered by line."""
    row = rules.get(RULE_EXCEPT_SWALLOW)
    if row is None or not row.enabled:
        return ()
    broad = frozenset(rule_strings(row, "broad_exceptions"))
    methods = frozenset(rule_strings(row, "logger_methods"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not _catches_broad(node, broad) or is_annotated(lines, node.lineno, marker):
            continue
        body = _walk_body(node.body)
        logs = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in methods
            for n in body
        )
        if logs and not any(isinstance(n, ast.Raise) for n in body):
            issues.append(
                detector_issue(row, path, lines, node.lineno, reason, remediation)
            )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_EXCEPT_SWALLOW", "check_except_swallow"]
