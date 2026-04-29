# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate 1 — banned T | None = None (and Optional[T] = None) for identity field names.

Identity fields (correlation_id, session_id, etc.) must never be optional with a
None default. Marking them optional silently breaks correlation chains and makes
distributed tracing unreliable.

parent_span_id is intentionally excluded — it is legitimately None for root spans.
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

IDENTITY_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "correlation_id",
        "session_id",
        "request_id",
        "trace_id",
        "span_id",
        "tenant_id",
        "agent_id",
        "node_id",
        "run_id",
        "handler_id",
        "user_id",
        "binding_id",
        "runtime_id",
    }
)


def _is_optional_with_none_default(
    annotation: ast.expr, default: ast.expr | None
) -> bool:
    """Return True if the annotation is T | None (or Optional[T]) AND default is None."""
    if default is None:
        return False
    if not isinstance(default, ast.Constant) or default.value is not None:
        return False
    return _annotation_is_optional(annotation)


def _annotation_is_optional(annotation: ast.expr) -> bool:
    """Return True if the annotation matches T | None or Optional[T]."""
    # T | None  (PEP 604 union)
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left, right = annotation.left, annotation.right
        if isinstance(right, ast.Constant) and right.value is None:
            return True
        if isinstance(left, ast.Constant) and left.value is None:
            return True
    # Optional[T]  (typing.Optional)
    if isinstance(annotation, ast.Subscript):
        value = annotation.value
        if isinstance(value, ast.Attribute) and value.attr == "Optional":
            return True
        if isinstance(value, ast.Name) and value.id == "Optional":
            return True
    return False


def _base_name_matches_basemodel(base: ast.expr) -> bool:
    """Return True for BaseModel references, including pydantic.BaseModel."""
    if isinstance(base, ast.Name):
        return base.id == "BaseModel"
    if isinstance(base, ast.Attribute):
        return base.attr == "BaseModel"
    if isinstance(base, ast.Subscript):
        return _base_name_matches_basemodel(base.value)
    return False


def _inherits_from_basemodel(node: ast.ClassDef) -> bool:
    return any(_base_name_matches_basemodel(base) for base in node.bases)


def _collect_basemodel_like_classes(tree: ast.Module) -> frozenset[str]:
    """Return local class names that directly or transitively inherit BaseModel."""
    class_nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    derived = {
        class_node.name
        for class_node in class_nodes
        if _inherits_from_basemodel(class_node)
    }

    changed = True
    while changed:
        changed = False
        for class_node in class_nodes:
            if class_node.name in derived:
                continue
            if any(
                isinstance(base, ast.Name) and base.id in derived
                for base in class_node.bases
            ):
                derived.add(class_node.name)
                changed = True

    return frozenset(derived)


class IdentityFieldOptionalityCheck(BaseGateCheck):
    """Gate 1: detect T | None = None (or Optional[T] = None) on identity fields."""

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []
        basemodel_like_classes = _collect_basemodel_like_classes(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in basemodel_like_classes:
                violations.extend(
                    self._check_pydantic_model_fields(node, source_lines, path)
                )

            # Function / async function arguments
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.extend(self._check_function_args(node, source_lines, path))

        return violations

    def _check_pydantic_model_fields(
        self,
        class_node: ast.ClassDef,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []

        for statement in class_node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            target = statement.target
            if not isinstance(target, ast.Name):
                continue
            field_name = target.id
            if field_name not in IDENTITY_FIELD_NAMES:
                continue
            if not _is_optional_with_none_default(
                statement.annotation, statement.value
            ):
                continue
            lineno = statement.lineno
            if has_allow_annotation(source_lines, lineno):
                continue
            violations.append(
                GateViolation(
                    path=path,
                    line=lineno,
                    message=(
                        f"identity field '{field_name}' must not be optional with a "
                        f"None default (T | None = None or Optional[T] = None); "
                        f"use a required field or add '# substrate-allow: <reason>'"
                    ),
                )
            )

        return violations

    def _check_function_args(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []
        args = func.args

        # Build list of (arg, default) pairs for regular args and kwonly args.
        # For regular args, defaults are right-aligned against the args list.
        all_regular_args = args.posonlyargs + args.args
        n_defaults = len(args.defaults)
        n_args = len(all_regular_args)
        # Pair each arg with its default (None if no default)
        paired: list[tuple[ast.arg, ast.expr | None]] = []
        for i, arg in enumerate(all_regular_args):
            default_offset = i - (n_args - n_defaults)
            default: ast.expr | None = (
                args.defaults[default_offset] if default_offset >= 0 else None
            )
            paired.append((arg, default))

        # kwonly args have 1:1 mapping with kw_defaults (None entries = no default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            paired.append((arg, default))

        for arg, default in paired:
            if arg.arg not in IDENTITY_FIELD_NAMES:
                continue
            if arg.annotation is None:
                continue
            if not _is_optional_with_none_default(arg.annotation, default):
                continue
            lineno = arg.lineno
            if has_allow_annotation(source_lines, lineno):
                continue
            violations.append(
                GateViolation(
                    path=path,
                    line=lineno,
                    message=(
                        f"identity field '{arg.arg}' must not be optional with a "
                        f"None default (T | None = None or Optional[T] = None); "
                        f"use a required parameter or add '# substrate-allow: <reason>'"
                    ),
                )
            )

        return violations


if __name__ == "__main__":
    sys.exit(main_for_gate(IdentityFieldOptionalityCheck()))
