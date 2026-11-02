# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure stub checker: path and bytes in, validation issues out (OMN-22003).

All markers, names, thresholds and diagnostic text are rule parameters in
``contracts/stub_implementations.validation.yaml``. This module performs no I/O.
The visitor retains the script's precedence and scope traversal, including
skipping nested functions inside exempt functions and inspecting only direct
body statements for raises and pass/return pairs.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)

__all__ = ["check_stub_implementations"]


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"stub_implementations rule {rule.rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def _text(rule: ModelValidatorRule, key: str) -> str:
    value = (rule.parameters or {}).get(key)
    if not isinstance(value, str) or not value.strip():
        raise _invalid(rule, f"parameter {key!r} must be a non-empty string")
    return value


def _texts(rule: ModelValidatorRule, key: str) -> list[str]:
    value = (rule.parameters or {}).get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise _invalid(rule, f"parameter {key!r} must be a list of non-empty strings")
    return value


def _threshold(rule: ModelValidatorRule, key: str) -> int:
    value = (rule.parameters or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _invalid(rule, f"parameter {key!r} must be a non-negative integer")
    return value


def _pattern(rule: ModelValidatorRule, key: str) -> re.Pattern[str]:
    try:
        return re.compile(_text(rule, key))
    except re.error as exc:
        raise _invalid(
            rule, f"parameter {key!r} is not a regular expression: {exc}"
        ) from exc


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


class _StubDetector(ast.NodeVisitor):
    """Preserve the legacy AST decisions, emitting the selected rule's findings."""

    def __init__(self, path: Path, lines: list[str], rule: ModelValidatorRule) -> None:
        self.path = path
        self.lines = lines
        self.rule = rule
        self.issues: list[ModelValidationIssue] = []
        self.in_exempt_class = False
        self.kind = _text(rule, "kind")
        if self.kind not in {
            "empty_body",
            "only_pass",
            "only_ellipsis",
            "not_implemented_error",
            "pass_return",
            "todo_in_docstring",
        }:
            raise _invalid(rule, f"unknown kind {self.kind!r}")
        self.path_pattern = _pattern(rule, "path_pattern")
        self.exempt_paths = _texts(rule, "exempt_path_markers")
        self.exempt_files = _texts(rule, "exempt_files")
        self.protocol_bases = _texts(rule, "protocol_base_names")
        self.abstract_bases = _texts(rule, "abstract_base_names")
        self.decorators = _texts(rule, "exempt_decorator_names")
        self.dunder_pattern = _pattern(rule, "dunder_pattern")
        self.checked_dunders = _texts(rule, "checked_dunder_names")
        leader = _text(rule, "approval_comment_leader")
        self.approvals = [
            f"{leader} {marker}" for marker in _texts(rule, "approval_markers")
        ]
        self.work_pattern = _pattern(rule, "work_item_pattern")
        self.exception_names = _texts(rule, "exception_names")
        self.single_count = _threshold(rule, "single_statement_count")
        self.docstring_limit = _threshold(rule, "docstring_excerpt_length")
        self.message = _text(rule, "message")
        _text(rule, "missing_target_message")
        self.remediation = _text(rule, "remediation")
        self.docstring_remediation = _text(rule, "docstring_remediation")
        self.default_remediation = _text(rule, "default_remediation")
        self.exact_names = _texts(rule, "suggestion_exact_names")
        self.exact_messages = _texts(rule, "suggestion_exact_messages")
        self.prefixes = _texts(rule, "suggestion_prefixes")
        self.prefix_messages = _texts(rule, "suggestion_prefix_messages")
        if len(self.exact_names) != len(self.exact_messages) or len(
            self.prefixes
        ) != len(self.prefix_messages):
            raise _invalid(
                rule, "suggestion names and messages must have equal lengths"
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old = self.in_exempt_class
        self.in_exempt_class = any(
            _name(base) in self.protocol_bases
            or (
                isinstance(base, ast.Subscript)
                and _name(base.value) in self.protocol_bases
            )
            or _name(base) in self.abstract_bases
            for base in node.bases
        )
        self.generic_visit(node)
        self.in_exempt_class = old

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)

    def _approved(self, line: int) -> bool:
        return line <= len(self.lines) and any(
            marker in self.lines[line - 1] for marker in self.approvals
        )

    def _exempt(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if self.in_exempt_class:
            return True
        if (
            self.dunder_pattern.search(node.name)
            and node.name not in self.checked_dunders
        ):
            return True
        if any(
            _name(decorator) in self.decorators for decorator in node.decorator_list
        ):
            return True
        return self._approved(node.lineno)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self._exempt(node):
            return
        docstring = ast.get_docstring(node, clean=False)
        statements = node.body[1:] if docstring is not None else node.body
        self._check_patterns(node, docstring, statements)
        self.generic_visit(node)

    def _check_patterns(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        docstring: str | None,
        statements: list[ast.stmt],
    ) -> None:
        if not statements:
            self._add("empty_body", node.lineno, node.name, docstring)
            return
        if len(statements) == self.single_count and isinstance(statements[0], ast.Pass):
            self._add("only_pass", node.lineno, node.name, docstring)
            return
        if len(statements) == self.single_count:
            stmt = statements[0]
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is Ellipsis
            ):
                self._add("only_ellipsis", node.lineno, node.name, docstring)
                return
        for stmt in statements:
            if isinstance(stmt, ast.Raise):
                exc = stmt.exc
                raised_name = (
                    _name(exc.func)
                    if isinstance(exc, ast.Call)
                    else exc.id
                    if isinstance(exc, ast.Name)
                    else None
                )
                if raised_name in self.exception_names and not self._approved(
                    stmt.lineno
                ):
                    self._add(
                        "not_implemented_error", stmt.lineno, node.name, docstring
                    )
                    return
        for index, stmt in enumerate(statements):
            if (
                isinstance(stmt, ast.Pass)
                and index + 1 < len(statements)
                and isinstance(statements[index + 1], ast.Return)
            ):
                self._add("pass_return", stmt.lineno, node.name, docstring)
        if docstring and self.work_pattern.search(docstring.upper()):
            self._add("todo_in_docstring", node.lineno, node.name, docstring)

    def _suggestion(self, name: str, docstring: str | None) -> str:
        for exact, message in zip(self.exact_names, self.exact_messages, strict=True):
            if name == exact:
                return message
        for prefix, message in zip(self.prefixes, self.prefix_messages, strict=True):
            if name.startswith(prefix):
                return message
        if docstring:
            return self.docstring_remediation.format(
                docstring=docstring[: self.docstring_limit]
            )
        return self.default_remediation

    def _add(self, kind: str, line: int, name: str, docstring: str | None) -> None:
        if kind != self.kind:
            return
        try:
            remediation = self.remediation.format(
                suggestion=self._suggestion(name, docstring)
            )
            detail = self.message.format(function_name=name)
        except (KeyError, ValueError, IndexError) as exc:
            raise _invalid(self.rule, f"invalid message template: {exc}") from exc
        self.issues.append(
            ModelValidationIssue(
                severity=self.rule.severity,
                message=f"{detail} -- {remediation}",
                code=self.rule.rule_id,
                rule_name=self.rule.rule_id,
                file_path=self.path,
                line_number=line,
            )
        )


def check_stub_implementations(
    file_path: Path,
    relative_path: str,
    content: bytes,
    rules: Sequence[ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Judge enabled rule rows, skipping syntax and encoding errors as before.

    Path markers are substring matches, as in the script. The old optional
    configuration's file and path exclusions are now contract parameters;
    its unused function exclusion list never influenced detection.
    """
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        detector = _StubDetector(file_path, [], rule)
        if (
            not detector.path_pattern.search(relative_path)
            or Path(relative_path).name in detector.exempt_files
            or any(marker in relative_path for marker in detector.exempt_paths)
        ):
            continue
        try:
            source = content.decode("utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeError):
            continue
        detector.lines = source.splitlines()
        detector.visit(tree)
        issues.extend(detector.issues)
    return tuple(issues)
