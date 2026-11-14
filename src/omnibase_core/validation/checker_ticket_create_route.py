# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``ticket_create_route`` (OMN-23770).

A direct Linear create issued outside the ticket node's handler skips the admission policy, the typed
draft and the receipt the node writes. Facts in (one module's path and source), ``ModelValidationIssue``
out. A Python module is read as a tree and a ``create_tokens`` entry is a finding when it stands in a
string constant that is not a docstring (the GraphQL mutation text); any other file is read line by
line, skipping lines that start with the comment prefix. A path that matches an ``allowed_path_patterns``
entry may hold the token. There is no baseline and no annotation.

The token, the allowed path patterns and the texts are ``parameters`` of the ``ticket_create_route`` rule
row of ``contracts/ticket_create_route.validation.yaml``; an enabled row with a missing or mistyped
parameter raises, so a broken contract fails to load instead of passing every file.
"""

from __future__ import annotations

import ast
import fnmatch
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_TICKET_CREATE_ROUTE = "ticket_create_route"


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


def _python_lines(source: str, tokens: tuple[str, ...]) -> list[int] | None:
    tree = parse_module(source)
    if tree is None:
        return None
    docstrings = _docstring_nodes(tree)
    return sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and any(token in node.value for token in tokens)
        }
    )


def _text_lines(source: str, tokens: tuple[str, ...], comment_prefix: str) -> list[int]:
    return [
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if not line.lstrip().startswith(comment_prefix)
        and any(token in line for token in tokens)
    ]


def check_ticket_create_route(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``ticket_create_route`` row, ordered by line."""
    row = rules.get(RULE_TICKET_CREATE_ROUTE)
    if row is None or not row.enabled:
        return ()
    tokens = rule_strings(row, "create_tokens")
    allowed = rule_strings(row, "allowed_path_patterns")
    comment_prefix = rule_string(row, "comment_prefix")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    rooted = f"/{path.as_posix()}"
    if any(fnmatch.fnmatch(rooted, pattern) for pattern in allowed):
        return ()
    line_numbers = (
        _python_lines(source, tokens)
        if path.suffix == ".py"
        else _text_lines(source, tokens, comment_prefix)
    )
    if not line_numbers:  # None: a module that does not parse is judged clean
        return ()
    lines = source.splitlines()
    return tuple(
        detector_issue(row, path, lines, number, reason, remediation)
        for number in line_numbers
    )


__all__ = ["RULE_TICKET_CREATE_ROUTE", "check_ticket_create_route"]
