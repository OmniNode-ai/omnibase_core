# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure single-class-per-file checker: facts in, issues out (OMN-22003).

The module judges one path and its bytes against the rule rows of
``contracts/single_class_per_file.validation.yaml``. Every exemption, enum
base marker, threshold and remediation text is a ``parameters`` entry of a
rule row. It performs no I/O: no file read, no clock, no environment.
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

__all__ = ["check_single_class_per_file"]


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    """A rule row that cannot be read is a load error, never a pass."""
    return ModelOnexError(
        message=f"single_class_per_file rule {rule.rule_id!r}: {detail}",
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


class _ClassDefinitionDetector(ast.NodeVisitor):
    """Collect classes using the legacy visitor's class/function scope tracking."""

    def __init__(self, enum_base_name_fragment: str) -> None:
        self.classes: list[tuple[int, str, bool]] = []
        self._enum_base_name_fragment = enum_base_name_fragment
        self._in_class = False
        self._in_function = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._in_class or self._in_function:
            return
        is_enum = any(
            self._enum_base_name_fragment in base.id
            if isinstance(base, ast.Name)
            else self._enum_base_name_fragment in base.attr
            if isinstance(base, ast.Attribute)
            else False
            for base in node.bases
        )
        self.classes.append((node.lineno, node.name, is_enum))
        self._in_class = True
        self.generic_visit(node)
        self._in_class = False


def check_single_class_per_file(
    file_path: Path,
    relative_path: str,
    content: bytes,
    rules: Sequence[ModelValidatorRule],
    *,
    repository_relative_path: str | None = None,
) -> tuple[ModelValidationIssue, ...]:
    """One issue per enabled rule that fires on this file, in rule order.

    ``relative_path`` retains the legacy path-marker semantics. The separate
    ``repository_relative_path`` fact is present only for files inside this
    repository, so canonical exemptions cannot exempt a shadow module elsewhere.
    Syntax errors and undecodable files are skipped, as in the script.
    """
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if not rule.enabled:
            continue
        path_pattern = _pattern(rule, "path_pattern")
        exempt_markers = _texts(rule, "exempt_path_markers")
        exempt_names = _texts(rule, "exempt_names")
        exempt_paths = _texts(rule, "exempt_repository_paths")
        scoped_name = _text(rule, "scoped_exempt_name")
        scoped_marker = _text(rule, "scoped_exempt_path_marker")
        enum_fragment = _text(rule, "enum_base_name_fragment")
        max_classes = _threshold(rule, "max_classes")
        message = _text(rule, "message")
        remediation = _text(rule, "remediation")
        name = Path(relative_path).name
        if (
            not path_pattern.search(relative_path)
            or any(marker in relative_path for marker in exempt_markers)
            or name in exempt_names
            or repository_relative_path in exempt_paths
            or (name == scoped_name and scoped_marker in relative_path)
        ):
            continue
        try:
            tree = ast.parse(content.decode("utf-8"), filename=str(file_path))
            detector = _ClassDefinitionDetector(enum_fragment)
            detector.visit(tree)
        except (SyntaxError, UnicodeError, ValueError, RecursionError):
            continue
        classes = detector.classes
        if len(classes) <= max_classes or all(is_enum for _, _, is_enum in classes):
            continue
        non_enum_count = sum(not is_enum for _, _, is_enum in classes)
        try:
            detail = message.format(
                non_enum_count=non_enum_count,
                enum_count=len(classes) - non_enum_count,
            )
        except (KeyError, ValueError, IndexError) as exc:
            raise _invalid(
                rule, f"parameter 'message' is not a message template: {exc}"
            ) from exc
        issues.append(
            ModelValidationIssue(
                severity=rule.severity,
                message=f"{detail} -- {remediation}",
                code=rule.rule_id,
                file_path=file_path,
                line_number=classes[0][0],
                rule_name=rule.rule_id,
            )
        )
    return tuple(issues)
