# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""AST visitor for no-new-os-environ validation."""

from __future__ import annotations

import ast
from collections.abc import Collection


class EnvReadVisitor(ast.NodeVisitor):
    """Walk an AST looking for os.environ / os.getenv reads."""

    def __init__(
        self,
        source_lines: list[str],
        *,
        keep_allowlist: Collection[str],
        suppression_marker: str,
    ) -> None:
        self._lines = source_lines
        self._keep_allowlist = keep_allowlist
        self._suppression_marker = suppression_marker
        self.findings: list[tuple[int, int, str]] = []

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect os.environ[KEY]."""
        if _is_os_environ_attr(node.value):
            var_name = _extract_constant_string(node.slice)
            if var_name is not None and self._should_flag(node.lineno, var_name):
                self.findings.append((node.lineno, node.col_offset, var_name))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect os.environ.get(KEY) and os.getenv(KEY)."""
        if _is_os_environ_get(node.func) or _is_os_getenv(node.func):
            var_name = _first_arg_string(node)
            if var_name is not None and self._should_flag(node.lineno, var_name):
                self.findings.append((node.lineno, node.col_offset, var_name))
        self.generic_visit(node)

    def _should_flag(self, lineno: int, var_name: str) -> bool:
        if var_name in self._keep_allowlist:
            return False
        raw = self._lines[lineno - 1] if lineno <= len(self._lines) else ""
        return self._suppression_marker not in raw


def _is_os_environ_attr(node: ast.expr) -> bool:
    """Return True for the ``os.environ`` attribute expression."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_os_environ_get(node: ast.expr) -> bool:
    """Return True for ``os.environ.get`` attribute chain."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "get"
        and _is_os_environ_attr(node.value)
    )


def _is_os_getenv(node: ast.expr) -> bool:
    """Return True for ``os.getenv`` attribute expression."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "getenv"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _extract_constant_string(node: ast.expr) -> str | None:
    """Extract a string constant from a subscript slice."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _first_arg_string(node: ast.Call) -> str | None:
    """Extract the first positional argument as a string constant, if any."""
    if node.args:
        return _extract_constant_string(node.args[0])
    return None
