# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``import_none_fallback`` (OMN-22005, replacing the OMN-10819 report-mode script).

``except ImportError: Symbol = None`` moves an import failure to the call site, where it
surfaces as an ``AttributeError`` or ``TypeError`` under specific code paths. Facts in (one
module's path and source), ``ModelValidationIssue`` out. The import error names, the
annotation marker (a comment prefix and a name) and the reason and remediation texts are ``parameters`` of the
``import_none_fallback`` rule row of ``contracts/import_none_fallback.validation.yaml``.
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

RULE_IMPORT_NONE_FALLBACK = "import_none_fallback"


def _catches_import_error(handler: ast.ExceptHandler, errors: frozenset[str]) -> bool:
    if isinstance(handler.type, ast.Name):
        return handler.type.id in errors
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(e, ast.Name) and e.id in errors for e in handler.type.elts
        )
    return False


def check_import_none_fallback(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``import_none_fallback`` row, ordered by line."""
    row = rules.get(RULE_IMPORT_NONE_FALLBACK)
    if row is None or not row.enabled:
        return ()
    errors = frozenset(rule_strings(row, "import_errors"))
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
        if not _catches_import_error(node, errors):
            continue
        for stmt in node.body:
            if not (
                isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is None
                and not is_annotated(lines, stmt.lineno, marker)
            ):
                continue
            issues.extend(
                detector_issue(row, path, lines, stmt.lineno, reason, remediation)
                for target in stmt.targets
                if isinstance(target, ast.Name)
            )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_IMPORT_NONE_FALLBACK", "check_import_none_fallback"]
