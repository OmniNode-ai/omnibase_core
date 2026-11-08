# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared pure helpers of the three AST detectors (OMN-22005, plan task T2.4).

``checker_except_swallow``, ``checker_none_guard_publish`` and ``checker_import_none_fallback``
parse one module, find nodes and report them under a rule row of their
``contracts/<id>.validation.yaml``. This module holds the parts they share: the parse that
tolerates an unparseable module, the source-line read, the annotation test and the issue.
No file read, no clock, no environment.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


def parse_module(source: str) -> ast.Module | None:
    """The module's tree; ``None`` for source that does not parse (it is judged clean)."""
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError):
        return None


def parse_baseline(text: str | None) -> dict[str, int]:
    """Path -> number of findings, from a YAML mapping; ``#`` lines are prose.

    Text that is not a mapping of paths to counts holds no entries, so a damaged
    baseline refuses every finding instead of admitting it.
    """
    try:
        loaded = load_yaml_mapping_no_duplicates(text or "{}", source="baseline")
    except (yaml.YAMLError, ValueError):
        return {}
    return {
        str(path): count
        for path, count in loaded.items()
        if isinstance(count, int) and not isinstance(count, bool)
    }


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Node -> its parent, for every node under ``tree``."""
    return {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }


def dotted_name(node: ast.expr) -> str:
    """``a.b.c`` for a Name or an Attribute chain over Names, else an empty string."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def source_line(lines: list[str], lineno: int) -> str:
    """Line ``lineno`` (1-based) of the module, or an empty string outside it."""
    return lines[lineno - 1] if 1 <= lineno <= len(lines) else ""


def is_annotated(lines: list[str], lineno: int, marker: str) -> bool:
    """Whether the annotation ``marker`` stands on line ``lineno``."""
    return marker in source_line(lines, lineno)


def detector_issue(
    row: ModelValidatorRule,
    path: Path,
    lines: list[str],
    lineno: int,
    reason: str,
    remediation: str,
) -> ModelValidationIssue:
    """One finding of ``row`` at ``lineno``: the rule's reason, the line, the remediation."""
    return ModelValidationIssue(
        severity=row.severity,
        message=f"{reason}: {source_line(lines, lineno).strip()} -- {remediation}",
        code=row.rule_id,
        file_path=path,
        line_number=lineno,
        rule_name=row.rule_id,
    )


__all__ = [
    "detector_issue",
    "dotted_name",
    "is_annotated",
    "parent_map",
    "parse_baseline",
    "parse_module",
    "source_line",
]
