# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate 3 — banned os.environ.get / os.getenv silent fallback with a default value.

Banned forms:
  os.environ.get("KEY", "default")   — explicit second arg
  os.getenv("KEY", "default")        — explicit second arg
  os.environ.get("KEY") or "default" — BoolOp Or with a constant right side

Allowed:
  os.environ["KEY"]                  — fail-fast KeyError
  os.environ.get("KEY")              — no default, returns None
  os.getenv("KEY")                   — no default, returns None
  ... # substrate-allow: bootstrap-fallback  (line-level suppression)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from omnibase_core.cli.substrate_gates._base import (
    BaseGateCheck,
    has_allow_annotation,
    main_for_gate,
)
from omnibase_core.cli.substrate_gates.gate_violation import GateViolation

_MSG_ENVIRON_GET = (
    "os.environ.get() called with a default — use os.environ[KEY] (fail-fast) "
    "or os.environ.get(KEY) with no default; annotate # substrate-allow: bootstrap-fallback "
    "for documented bootstrap cases"
)
_MSG_GETENV = (
    "os.getenv() called with a default — use os.environ[KEY] (fail-fast) "
    "or os.getenv(KEY) with no default; annotate # substrate-allow: bootstrap-fallback "
    "for documented bootstrap cases"
)
_MSG_BOOL_OR = (
    "os.environ.get() result used in `or <default>` — use os.environ[KEY] (fail-fast) "
    "or os.environ.get(KEY) with explicit None-check; annotate # substrate-allow: bootstrap-fallback "
    "for documented bootstrap cases"
)


def _is_environ_get_call(node: ast.AST) -> bool:
    """Return True if node is os.environ.get(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "environ"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "os"
    )


def _is_getenv_call(node: ast.AST) -> bool:
    """Return True if node is os.getenv(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "getenv"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
    )


class EnvSilentFallbackGate(BaseGateCheck):
    """Detect os.environ.get / os.getenv calls that silently supply a default value."""

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []

        for node in ast.walk(tree):
            # --- Variant 3: BoolOp Or whose left side is environ.get() ---
            if (
                isinstance(node, ast.BoolOp)
                and isinstance(node.op, ast.Or)
                and len(node.values) >= 2
                and _is_environ_get_call(node.values[0])
                and isinstance(node.values[1], ast.Constant)
            ):
                lineno = node.lineno
                if not has_allow_annotation(source_lines, lineno):
                    violations.append(
                        GateViolation(path=path, line=lineno, message=_MSG_BOOL_OR)
                    )
                # Don't also flag the inner call as a Variant 1 violation.
                continue

            # --- Variant 1: os.environ.get(KEY, default) ---
            if isinstance(node, ast.Call) and _is_environ_get_call(node):
                if len(node.args) >= 2 or any(
                    kw.arg == "default" for kw in node.keywords
                ):
                    lineno = node.lineno
                    if not has_allow_annotation(source_lines, lineno):
                        violations.append(
                            GateViolation(
                                path=path, line=lineno, message=_MSG_ENVIRON_GET
                            )
                        )

            # --- Variant 2: os.getenv(KEY, default) ---
            if isinstance(node, ast.Call) and _is_getenv_call(node):
                if len(node.args) >= 2 or any(
                    kw.arg == "default" for kw in node.keywords
                ):
                    lineno = node.lineno
                    if not has_allow_annotation(source_lines, lineno):
                        violations.append(
                            GateViolation(path=path, line=lineno, message=_MSG_GETENV)
                        )

        return violations


def main(argv: list[str] | None = None) -> int:
    return main_for_gate(EnvSilentFallbackGate(), argv)


if __name__ == "__main__":
    sys.exit(main())
