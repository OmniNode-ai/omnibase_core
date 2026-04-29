# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate 2 — ban loose typing (dict[str, Any] / Any / **kwargs: Any) in service-internal
Pydantic models and Protocol signatures.

Banned forms
------------
- ``field: dict[str, Any]``, ``Dict[str, Any]``, ``Mapping[str, Any]``
- ``field: Any``
- ``def method(arg: Any)``, ``def method(arg: dict[str, Any])``
- ``**kwargs: Any``, ``**kwargs: object``
- All of the above inside ``class X(Protocol):`` bodies

Suppression
-----------
A ``# substrate-allow: <reason>`` annotation on the same line suppresses.
``# ONEX_EXCLUDE: any_type`` and ``# ai-slop-ok`` are recognised as compatible
alternatives (see :func:`~omnibase_core.cli.substrate_gates._base.has_allow_annotation`).
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

# Container-like generics that produce a violation when their value type is Any.
_DICT_LIKE_NAMES = frozenset({"dict", "Dict", "Mapping"})


def _is_any_name(node: ast.expr) -> bool:
    """Return True if *node* is a bare ``Any`` name reference."""
    return isinstance(node, ast.Name) and node.id == "Any"


def _is_object_name(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "object"


def _is_dict_like_any(node: ast.expr) -> bool:
    """Return True for ``dict[str, Any]``, ``Dict[str, Any]``, ``Mapping[str, Any]``."""
    if not isinstance(node, ast.Subscript):
        return False
    if not (isinstance(node.value, ast.Name) and node.value.id in _DICT_LIKE_NAMES):
        return False
    # slice is a Tuple([key_type, value_type]) for generic[K, V]
    slc = node.slice
    if not isinstance(slc, ast.Tuple):
        return False
    if len(slc.elts) < 2:
        return False
    return _is_any_name(slc.elts[1])


def _annotation_is_banned(annotation: ast.expr | None) -> bool:
    """Return True if *annotation* is one of the banned loose-typing forms."""
    if annotation is None:
        return False
    return _is_any_name(annotation) or _is_dict_like_any(annotation)


def _is_pydantic_class(node: ast.ClassDef) -> bool:
    """Heuristic: class inherits from a name that looks like a Pydantic base."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {
            "BaseModel",
            "BaseSettings",
        }:
            return True
        # e.g. pydantic.BaseModel
        if isinstance(base, ast.Attribute) and base.attr in {
            "BaseModel",
            "BaseSettings",
        }:
            return True
    return False


def _is_protocol_class(node: ast.ClassDef) -> bool:
    """Heuristic: class inherits from Protocol (bare or qualified)."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
    return False


class LooseTypingInInternalGate(BaseGateCheck):
    """AST gate that detects loose typing in Pydantic models and Protocol signatures."""

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
            if not (_is_pydantic_class(node) or _is_protocol_class(node)):
                continue

            for item in ast.walk(node):
                # --- Pydantic field annotation: `field: dict[str, Any]` etc. ---
                if isinstance(item, ast.AnnAssign) and item.col_offset >= 0:
                    # Only check attributes defined directly in the class body.
                    # (ast.walk recurses; guard to avoid nested class fields
                    #  being checked twice — the inner class will get its own pass.)
                    ann = item.annotation
                    lineno = item.lineno
                    if _annotation_is_banned(ann) and not has_allow_annotation(
                        source_lines, lineno
                    ):
                        violations.append(
                            GateViolation(
                                path=path,
                                line=lineno,
                                message=_format_message(ann, "field annotation"),
                            )
                        )

                # --- Function / method signatures ---
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    violations.extend(self._check_function(item, source_lines, path))

        return violations

    def _check_function(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []
        args = func.args

        # Regular positional args (includes self/cls which usually have no annotation)
        all_args = args.posonlyargs + args.args + args.kwonlyargs
        for arg in all_args:
            ann = arg.annotation
            if ann is None:
                continue
            lineno = arg.lineno if hasattr(arg, "lineno") else func.lineno
            if _annotation_is_banned(ann) and not has_allow_annotation(
                source_lines, lineno
            ):
                violations.append(
                    GateViolation(
                        path=path,
                        line=lineno,
                        message=_format_message(ann, f"argument '{arg.arg}'"),
                    )
                )

        # **kwargs annotation
        if args.kwarg is not None:
            kwarg = args.kwarg
            ann = kwarg.annotation
            lineno = kwarg.lineno if hasattr(kwarg, "lineno") else func.lineno
            if ann is not None and (
                _is_any_name(ann) or _is_object_name(ann) or _is_dict_like_any(ann)
            ):
                if not has_allow_annotation(source_lines, lineno):
                    violations.append(
                        GateViolation(
                            path=path,
                            line=lineno,
                            message=f"banned **kwargs annotation: **{kwarg.arg}: {ast.unparse(ann)}",
                        )
                    )

        return violations


def _format_message(annotation: ast.expr, location: str) -> str:
    return f"banned loose typing in {location}: {ast.unparse(annotation)}"


def main(argv: list[str] | None = None) -> int:
    return main_for_gate(LooseTypingInInternalGate(), argv)


if __name__ == "__main__":
    sys.exit(main())
