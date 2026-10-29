# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerDictAny -- detects ``dict[str, Any]`` annotations.

``dict[str, Any]`` defeats strong typing: no compile-time safety, dangerous
refactors, hidden bugs. A function or class carrying an allow decorator, or a line
under an exclusion comment, is exempt; the decorator names, the skipped path
fragments and the exclusion marker are rule data (``contracts/dict_any_rules.yaml``).

Pure: no filesystem, no clock, no global state. Ticket: OMN-21501.
"""

from __future__ import annotations

import ast

from omnibase_core.handlers.handler_finding_baseline import normalize_text
from omnibase_core.models.dict_any.model_dict_any_check_input import (
    ModelDictAnyCheckInput,
)
from omnibase_core.models.dict_any.model_dict_any_rules import ModelDictAnyRules
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["RULE_DICT_ANY", "RULE_FILE_ERROR", "HandlerDictAny"]

RULE_DICT_ANY = "dict-any"
RULE_FILE_ERROR = "file-error"


def _is_str_any(slice_node: ast.expr) -> bool:
    if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) == 2:
        first, second = slice_node.elts
        return (
            isinstance(first, ast.Name)
            and first.id == "str"
            and isinstance(second, ast.Name)
            and second.id == "Any"
        )
    return False


def _is_allowed_def(node: ast.AST, allow: frozenset[str]) -> bool:
    if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id in allow:
            return True
    return False


def _finding_lines(
    tree: ast.AST, rules: ModelDictAnyRules, excluded: set[int]
) -> list[int]:
    """Lines of dict[str, Any] subscripts outside decorated or excluded code."""
    allow = frozenset(rules.allow_decorators)
    allowed = set(excluded)
    for node in ast.walk(tree):
        if _is_allowed_def(node, allow):
            allowed.update(
                child.lineno for child in ast.walk(node) if hasattr(child, "lineno")
            )
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "dict"
        and _is_str_any(node.slice)
        and node.lineno not in allowed
    )


def _excluded_lines(source_lines: list[str], rules: ModelDictAnyRules) -> set[int]:
    marker = "".join(rules.exclude_marker_parts)
    excluded: set[int] = set()
    for number, line in enumerate(source_lines, start=1):
        if marker in line and rules.exclude_tag in line:
            excluded.update(range(number, number + rules.exclude_window_lines + 1))
    return excluded


class HandlerDictAny:
    """COMPUTE handler: ``dict[str, Any]`` findings over explicit (path, source) pairs."""

    def handle(self, request: ModelDictAnyCheckInput) -> ModelFindingDetectResult:
        """Typed request in, typed findings out."""
        findings: list[ModelSourceFinding] = []
        checked = 0
        for file in sorted(request.files, key=lambda f: f.path):
            if any(
                fragment in file.path for fragment in request.rules.skip_path_fragments
            ):
                continue
            checked += 1
            source_lines = file.source.split("\n")
            try:
                tree = ast.parse(file.source, filename=file.path)
            except SyntaxError as exc:
                findings.append(
                    ModelSourceFinding(
                        path=file.path,
                        line=exc.lineno or 0,
                        rule=RULE_FILE_ERROR,
                        text="",
                        message=f"Syntax error: {exc.msg}",
                        baselinable=False,
                    )
                )
                continue
            excluded = _excluded_lines(source_lines, request.rules)
            for line in _finding_lines(tree, request.rules, excluded):
                text = source_lines[line - 1] if line <= len(source_lines) else ""
                findings.append(
                    ModelSourceFinding(
                        path=file.path,
                        line=line,
                        rule=RULE_DICT_ANY,
                        text=normalize_text(text),
                        message="dict[str, Any] anti-pattern detected",
                    )
                )
        return ModelFindingDetectResult(findings=tuple(findings), files_checked=checked)
