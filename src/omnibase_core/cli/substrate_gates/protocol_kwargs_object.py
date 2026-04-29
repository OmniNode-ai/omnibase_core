# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate 5 — banned ``**kwargs: object`` / ``**kwargs: Any`` in Protocol method signatures.

Detects ``*args: object``, ``*args: Any``, ``**kwargs: object``, ``**kwargs: Any``
inside ``class X(Protocol):`` bodies only.  Regular (non-Protocol) classes are
ignored.  The ``# substrate-allow:`` annotation on the ``def`` line suppresses.
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

_BANNED_NAMES = frozenset({"object", "Any"})


def _is_protocol_class(node: ast.ClassDef) -> bool:
    """Return True if *node* has ``Protocol`` as a direct base."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
    return False


def _annotation_name(annotation: ast.expr | None) -> str | None:
    """Extract a simple name string from an annotation node, or None."""
    if annotation is None:
        return None
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    return None


class ProtocolKwargsObjectGate(BaseGateCheck):
    """Gate 5: no ``*args: object/Any`` or ``**kwargs: object/Any`` in Protocol methods."""

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not _is_protocol_class(node):
                continue

            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue

                args = item.args
                lineno = item.lineno

                if has_allow_annotation(source_lines, lineno):
                    continue

                vararg_name = _annotation_name(
                    args.vararg.annotation if args.vararg else None
                )
                kwarg_name = _annotation_name(
                    args.kwarg.annotation if args.kwarg else None
                )

                if vararg_name in _BANNED_NAMES:
                    violations.append(
                        GateViolation(
                            path=path,
                            line=lineno,
                            message=(
                                f"Protocol method '{item.name}' uses banned"
                                f" *args: {vararg_name} — use explicit typed parameters"
                            ),
                        )
                    )

                if kwarg_name in _BANNED_NAMES:
                    violations.append(
                        GateViolation(
                            path=path,
                            line=lineno,
                            message=(
                                f"Protocol method '{item.name}' uses banned"
                                f" **kwargs: {kwarg_name} — use explicit typed parameters"
                            ),
                        )
                    )

        return violations


def main(argv: list[str] | None = None) -> int:
    return main_for_gate(ProtocolKwargsObjectGate(), argv)


if __name__ == "__main__":
    sys.exit(main())
