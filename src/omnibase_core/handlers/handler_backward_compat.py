# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure backcompat detection over explicit source pairs (OMN-21501).

Rules come from the contract. Independent regex and AST matches intentionally
remain separate findings, including multiple matches on the same source line.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator

from omnibase_core.handlers.handler_finding_baseline import normalize_text
from omnibase_core.models.backward_compat.model_backward_compat_check_input import (
    ModelBackwardCompatCheckInput,
)
from omnibase_core.models.backward_compat.model_backward_compat_rules import (
    ModelBackwardCompatRules,
)
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["HandlerBackwardCompat"]


def _check_text_patterns(
    content: str,
    lines: list[str],
    rules: ModelBackwardCompatRules,
    emit: Callable[[int, str, str], None],
) -> None:
    """Preserve the original pattern order, exclusions and duplicate reporting."""
    for number, line in enumerate(lines, 1):
        lower = line.lower()
        if any(re.search(pattern, lower) for pattern in rules.negative_patterns):
            continue
        for pattern in rules.compatibility_comment_patterns:
            if re.search(pattern, lower):
                emit(number, "compat-comment", line.strip())

    flags = re.MULTILINE | re.IGNORECASE
    for pattern in rules.compatibility_method_patterns:
        for match in re.finditer(pattern, content, flags):
            emit(content[: match.start()].count("\n") + 1, "compat-method", "")
    for match in re.finditer(rules.deprecated_method_pattern, content, flags):
        name = re.search(rules.method_name_pattern, match.group(0))
        if name and name.group(1) not in rules.legitimate_deprecated_methods:
            emit(content[: match.start()].count("\n") + 1, "compat-method", "")

    for pattern in rules.extra_allow_same_line_patterns:
        for match in re.finditer(pattern, content, flags):
            emit(content[: match.start()].count("\n") + 1, "compat-extra-allow", "")
    for match in re.finditer(rules.extra_allow_pattern, content, flags):
        number = content[: match.start()].count("\n") + 1
        start = max(0, number - 1 - rules.extra_allow_context_before)
        end = min(len(lines), number + rules.extra_allow_context_after)
        context = "\n".join(lines[start:end]).lower()
        if any(
            keyword in context for keyword in rules.extra_allow_keywords
        ) and not any(
            re.search(pattern, lines[number - 1], re.IGNORECASE)
            for pattern in rules.extra_allow_same_line_patterns
        ):
            emit(number, "compat-extra-allow", "")

    for pattern in rules.protocol_compat_patterns:
        for match in re.finditer(pattern, content, flags):
            number = content[: match.start()].count("\n") + 1
            line = content.splitlines()[number - 1].strip()
            if line.startswith(rules.protocol_import_prefixes) or (
                rules.protocol_assignment_marker in line
                and rules.protocol_import_keyword not in line
            ):
                continue
            emit(number, "compat-protocol", "")


def _preorder(node: ast.AST) -> Iterator[ast.AST]:
    """Depth-first, field order: the order ``ast.NodeVisitor`` visits nodes in."""
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _preorder(child)


def _check_ast(
    tree: ast.AST,
    source_lines: list[str],
    rules: ModelBackwardCompatRules,
    emit: Callable[[int, str, str], None],
) -> None:
    for node in _preorder(tree):
        if isinstance(node, ast.If):
            _check_if(node, source_lines, rules, emit)
        elif isinstance(node, ast.FunctionDef):
            _check_function(node, rules, emit)


def _check_if(
    node: ast.If,
    source_lines: list[str],
    rules: ModelBackwardCompatRules,
    emit: Callable[[int, str, str], None],
) -> None:
    test = node.test
    if not (
        isinstance(test, ast.Call)
        and isinstance(test.func, ast.Attribute)
        and test.func.attr == rules.startswith_method
        and test.args
        and isinstance(test.args[0], ast.Constant)
        and test.args[0].value == rules.protocol_startswith_constant
    ):
        return
    start = max(0, node.lineno - 1 - rules.protocol_condition_context_before)
    end = min(len(source_lines), node.lineno + rules.protocol_condition_context_after)
    context = "\n".join(source_lines[start:end]).lower()
    if any(keyword in context for keyword in rules.protocol_condition_keywords):
        emit(node.lineno, "compat-protocol-condition", "")


def _check_function(
    node: ast.FunctionDef,
    rules: ModelBackwardCompatRules,
    emit: Callable[[int, str, str], None],
) -> None:
    if (
        node.name.startswith(rules.dunder_marker)
        and node.name.endswith(rules.dunder_marker)
    ) or node.name in rules.legitimate_deprecated_methods:
        return
    for suffix in rules.function_name_suffixes:
        if node.name.endswith(suffix):
            emit(node.lineno, "compat-function-name", node.name)
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        docstring = node.body[0].value.value.lower()
        if any(phrase in docstring for phrase in rules.docstring_phrases):
            emit(node.lineno, "compat-docstring", node.name)


def _detect_file(
    path: str, source: str, rules: ModelBackwardCompatRules
) -> list[ModelSourceFinding]:
    """Detect one file with an emitter bound to its source and label."""
    findings: list[ModelSourceFinding] = []
    lines = source.split("\n")
    file_findings: list[ModelSourceFinding] = []

    def emit(line: int, rule: str, detail: str) -> None:
        file_findings.append(
            ModelSourceFinding(
                path=path,
                line=line,
                rule=rule,
                text=normalize_text(lines[line - 1]) if 0 < line <= len(lines) else "",
                message=rules.messages[rule].format(line=detail, name=detail),
            )
        )

    _check_text_patterns(source, lines, rules, emit)
    # Failed parses discard regex findings, as the old detector did.
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError, MemoryError) as exc:
        line = 0
        if isinstance(exc, SyntaxError):
            line = exc.lineno or 0
            message = f"Python syntax error at line {exc.lineno}, column {exc.offset}: {exc.msg}"
        elif isinstance(exc, ValueError):
            message = f"Invalid Python code - {exc}"
        else:
            message = "File too large to parse in memory"
        findings.append(
            ModelSourceFinding(
                path=path,
                line=line,
                rule="file-error",
                text=normalize_text(lines[line - 1]) if 0 < line <= len(lines) else "",
                message=message,
                baselinable=False,
            )
        )
        return findings
    _check_ast(tree, lines, rules, emit)
    return file_findings


class HandlerBackwardCompat:
    """COMPUTE handler: source text and rule data in, located findings out."""

    def handle(
        self, request: ModelBackwardCompatCheckInput
    ) -> ModelFindingDetectResult:
        """Detect patterns without reading files or mutating the request."""
        findings: list[ModelSourceFinding] = []
        for file in sorted(request.files, key=lambda item: item.path):
            if any(
                fragment in file.path
                for fragment in request.rules.architectural_exemptions
            ):
                continue
            findings.extend(_detect_file(file.path, file.source, request.rules))
        return ModelFindingDetectResult(
            findings=tuple(findings), files_checked=len(request.files)
        )
