# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reference finding sets of the three report-mode scripts the generic checkers replaced (OMN-22005).

``validate_no_except_swallow.py`` (OMN-10817), ``validate_no_none_guard_publish.py`` (OMN-10818)
and ``validate_no_import_none_fallback.py`` (OMN-10819) were removed in the change that added the
checkers. Their detection logic is restated here, with the scripts' own name sets (the annotation marker is passed in), so that the
verdict-parity tests compare the checkers with what the scripts found on the same source.
"""

from __future__ import annotations

import ast

_BROAD = {"Exception", "BaseException"}
_LOGGER = {"warning", "info", "debug", "error", "critical", "exception"}
_BUS = {"_event_bus", "event_bus", "_bus", "bus"}
_PUBLISH = {"publish", "emit", "send", "dispatch"}
_IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError"}


def _walk(body: list[ast.stmt]) -> list[ast.AST]:
    return list(ast.walk(ast.Module(body=body, type_ignores=[])))


def _names(type_node: ast.expr | None, wanted: set[str]) -> bool:
    if isinstance(type_node, ast.Name):
        return type_node.id in wanted
    if isinstance(type_node, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in wanted for e in type_node.elts)
    return False


def _is_bus(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id in _BUS
    return isinstance(node, ast.Attribute) and node.attr in _BUS


def except_swallow_lines(source: str, marker: str) -> list[int]:
    lines = source.splitlines()
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not (node.type is None or _names(node.type, _BROAD)):
            continue
        if marker in lines[node.lineno - 1]:
            continue
        body = _walk(node.body)
        logs = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in _LOGGER
            for n in body
        )
        if logs and not any(isinstance(n, ast.Raise) for n in body):
            found.append(node.lineno)
    return sorted(found)


def none_guard_publish_lines(source: str, marker: str) -> list[int]:
    lines = source.splitlines()
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.If) or marker in lines[node.lineno - 1]:
            continue
        test = node.test
        guarded = (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.IsNot)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value is None
            and _is_bus(test.left)
        ) or (isinstance(test, (ast.Name, ast.Attribute)) and _is_bus(test))
        if guarded and any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in _PUBLISH
            and _is_bus(n.func.value)
            for n in _walk(node.body)
        ):
            found.append(node.lineno)
    return sorted(found)


def import_none_fallback_lines(source: str, marker: str) -> list[int]:
    lines = source.splitlines()
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.ExceptHandler) and _names(node.type, _IMPORT_ERRORS)
        ):
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is None
                and marker not in lines[stmt.lineno - 1]
            ):
                found.extend(
                    stmt.lineno for t in stmt.targets if isinstance(t, ast.Name)
                )
    return sorted(found)
