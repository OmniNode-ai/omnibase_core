# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``effect_node_bypass`` (OMN-24432).

An outside-world call issued from anywhere but its effect node skips the node's contract, its overlay
values, its typed result and its receipt. Facts in (one module's path and source), ``ModelValidationIssue``
out: no file read, no clock, no environment.

Each rule row of ``contracts/effect_node_bypass.validation.yaml`` names one outside surface. A Python
module is read as a tree: a list or tuple literal whose first word is one of the row's
``command_executables`` and that holds a further element (a command line), a call whose first argument
is a command string starting with one, and a string constant that is not a docstring and holds one of the
row's ``string_substrings`` are findings. Any other file is read line by line, skipping lines that start
with the comment prefix, against the row's ``text_line_patterns``. A path that matches an
``allowed_path_patterns`` entry (the effect node packages) may hold the call.

Every executable, substring, pattern, path pattern and text is a ``parameters`` entry of a rule row; an
enabled row with a missing or mistyped parameter, or a pattern that does not compile, raises, so a broken
contract fails to load instead of passing every file.

The count ratchet is the ``count_ratchet`` row: the number of findings in the whole run may not exceed the
repository's count file, may not sit below it (a removal lowers the file in the same change), and the file
may not be raised against the base revision. ``check_count_ratchet`` judges the three numbers; the validator
reads them.
"""

from __future__ import annotations

import ast
import fnmatch
import re
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_COUNT_RATCHET = "count_ratchet"


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """The ids of the constant nodes that are a module, class or function docstring."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _is_executable(word: str, executables: tuple[str, ...]) -> bool:
    return any(word == e or word.endswith(f"/{e}") for e in executables)


def _head_word(node: ast.expr) -> str | None:
    """The first word of a command given as a string constant or as a list or tuple literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        words = node.value.split()
        return words[0] if words else None
    if isinstance(node, ast.List | ast.Tuple) and len(node.elts) >= 2:
        head = node.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    return None


def _python_lines(
    tree: ast.Module, executables: tuple[str, ...], substrings: tuple[str, ...]
) -> set[int]:
    docstrings = _docstring_nodes(tree)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.List | ast.Tuple):
            word = _head_word(node)
            if word is not None and _is_executable(word, executables):
                lines.add(node.lineno)
        elif isinstance(node, ast.Call) and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant):
                word = _head_word(first)
                if word is not None and _is_executable(word, executables):
                    lines.add(node.lineno)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and any(s in node.value for s in substrings)
        ):
            lines.add(node.lineno)
    return lines


def _patterns(row: ModelValidatorRule, key: str) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for pattern in rule_strings(row, key):
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise ModelOnexError(
                message=f"effect_node_bypass rule {row.rule_id!r}: parameters.{key} "
                f"holds an invalid regular expression {pattern!r}: {exc}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            ) from exc
    return tuple(compiled)


def _text_lines(
    source: str, patterns: tuple[re.Pattern[str], ...], comment_prefix: str
) -> set[int]:
    return {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if not line.lstrip().startswith(comment_prefix)
        and any(p.search(line) for p in patterns)
    }


def _row_issues(
    row: ModelValidatorRule, path: Path, source: str
) -> tuple[ModelValidationIssue, ...]:
    executables = rule_strings(row, "command_executables")
    substrings = rule_strings(row, "string_substrings")
    patterns = _patterns(row, "text_line_patterns")
    allowed = rule_strings(row, "allowed_path_patterns")
    comment_prefix = rule_string(row, "comment_prefix")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    rooted = f"/{path.as_posix()}"
    if any(fnmatch.fnmatch(rooted, pattern) for pattern in allowed):
        return ()
    if path.suffix == ".py":
        tree = parse_module(source)
        if tree is None:  # a module that does not parse is judged clean
            return ()
        numbers = _python_lines(tree, executables, substrings)
    else:
        numbers = _text_lines(source, patterns, comment_prefix)
    lines = source.splitlines()
    return tuple(
        detector_issue(row, path, lines, number, reason, remediation)
        for number in sorted(numbers)
    )


def check_effect_node_bypass(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under every enabled surface row, ordered by row then line."""
    issues: list[ModelValidationIssue] = []
    for rule_id, row in rules.items():
        if rule_id == RULE_COUNT_RATCHET or not row.enabled:
            continue
        issues.extend(_row_issues(row, path, source))
    return tuple(issues)


def check_count_ratchet(
    count: int,
    ratchet: int,
    base_ratchet: int | None,
    ratchet_path: Path,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for the whole run's count against the count file and the base revision's count file."""
    row = rules.get(RULE_COUNT_RATCHET)
    if row is None or not row.enabled:
        return ()
    values = {
        "path": ratchet_path.as_posix(),
        "count": count,
        "ratchet": ratchet,
        "base": base_ratchet,
    }
    messages: list[str] = []
    if count > ratchet:
        messages.append(rule_string(row, "grew_message").format(**values))
    if count < ratchet:
        messages.append(rule_string(row, "stale_message").format(**values))
    if base_ratchet is not None and ratchet > base_ratchet:
        messages.append(rule_string(row, "growth_message").format(**values))
    return tuple(
        ModelValidationIssue(
            severity=row.severity,
            message=message,
            code=row.rule_id,
            file_path=ratchet_path,
            line_number=1,
            rule_name=row.rule_id,
        )
        for message in messages
    )


__all__ = [
    "RULE_COUNT_RATCHET",
    "check_count_ratchet",
    "check_effect_node_bypass",
]
