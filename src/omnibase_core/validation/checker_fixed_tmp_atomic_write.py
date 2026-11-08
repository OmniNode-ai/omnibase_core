# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``fixed_tmp_atomic_write`` (OMN-23188).

A write-then-rename publishes a file atomically only while no other writer shares the temporary file.
A temporary path that is the target path plus a fixed suffix (``target.tmp``) is the same path for
every writer, so two concurrent writers truncate and rename each other's half-written data. Facts in
(one module's path and source), ``ModelValidationIssue`` out.

The rename is found as a call of a ``rename_functions`` entry (``os.replace(tmp, target)``) or a
``rename_methods`` entry with one argument (``tmp.replace(target)``). The temporary path is the
expression handed to it, followed through the plain assignments before it in the same function. It is
refused when it holds a string constant and every path name in it also stands in the target. A name that
is not in the target (a pid, a uuid, a ``mkstemp`` result, a parameter) is what makes the path differ per
writer or lets it come from elsewhere, so such a path is admitted; so is a call that is not a
``path_derivations`` callable, which counts as one such name, as written.

The names, the annotation marker and the reason and remediation texts are ``parameters`` of the
``fixed_tmp_atomic_write`` rule row of ``contracts/fixed_tmp_atomic_write.validation.yaml``; an enabled
row with a missing or mistyped parameter raises, so a broken contract fails to load instead of passing
every file.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_FIXED_TMP_ATOMIC_WRITE = "fixed_tmp_atomic_write"

_Scope = ast.Module | ast.FunctionDef | ast.AsyncFunctionDef


_Names = Mapping[str, frozenset[str]]
_Shape = tuple[
    bool, frozenset[str]
]  # (holds a string constant, the path names it is made of)


def _dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _tail(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _scopes(tree: ast.Module) -> list[tuple[_Scope, list[ast.AST]]]:
    """Each scope with the nodes that belong to it and not to a nested function."""
    scopes: list[tuple[_Scope, list[ast.AST]]] = []

    def own(scope: _Scope) -> list[ast.AST]:
        nodes: list[ast.AST] = []
        pending: list[ast.AST] = list(ast.iter_child_nodes(scope))
        while pending:
            node = pending.pop()
            nodes.append(node)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            pending.extend(ast.iter_child_nodes(node))
        return nodes

    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef):
            scopes.append((node, own(node)))
    return scopes


class _Reader:
    """Reads the shape of a path expression in one scope, following plain assignments."""

    def __init__(self, nodes: list[ast.AST], names: _Names) -> None:
        self._names = names
        self._assigned: dict[str, list[tuple[int, ast.expr]]] = {}
        for node in nodes:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = _dotted(node.targets[0])
                if target is not None:
                    self._assigned.setdefault(target, []).append(
                        (node.lineno, node.value)
                    )
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                target = _dotted(node.target)
                if target is not None:
                    self._assigned.setdefault(target, []).append(
                        (node.lineno, node.value)
                    )

    def shape(self, node: ast.expr, before: int) -> _Shape:
        constant = False
        leaves: set[str] = set()
        pending: list[tuple[ast.AST, int]] = [(node, before)]
        while pending:
            current, line = pending.pop()
            if isinstance(current, ast.Constant):
                constant = constant or isinstance(current.value, str)
            elif isinstance(current, ast.Call):
                tail = _tail(current.func)
                if tail in self._names["path_derivations"]:
                    if isinstance(current.func, ast.Attribute):
                        pending.append((current.func.value, line))
                    pending.extend((a, line) for a in current.args)
                    pending.extend((k.value, line) for k in current.keywords)
                else:
                    leaves.add(ast.unparse(current))
            elif isinstance(current, ast.Name | ast.Attribute):
                dotted = _dotted(current)
                if dotted is None:
                    pending.extend((c, line) for c in ast.iter_child_nodes(current))
                    continue
                found = self._assignment(dotted, line)
                if found is not None:
                    pending.append(found)
                else:
                    leaves.add(self._normalised(dotted))
            else:
                pending.extend((c, line) for c in ast.iter_child_nodes(current))
        return (constant, frozenset(leaves))

    def _assignment(self, dotted: str, line: int) -> tuple[ast.expr, int] | None:
        earlier = [a for a in self._assigned.get(dotted, []) if a[0] < line]
        if not earlier:
            return None
        lineno, value = max(earlier, key=lambda a: a[0])
        return value, lineno

    def _normalised(self, dotted: str) -> str:
        parts = dotted.split(".")
        while len(parts) > 1 and parts[-1] in self._names["derived_attributes"]:
            parts.pop()
        return ".".join(parts)


def _rename_operands(call: ast.Call, names: _Names) -> tuple[ast.expr, ast.expr] | None:
    """The (temporary, target) expressions of a rename call, or ``None`` for another call."""
    dotted = _dotted(call.func)
    if call.keywords or any(isinstance(a, ast.Starred) for a in call.args):
        return None
    if dotted in names["rename_functions"] and len(call.args) == 2:
        return call.args[0], call.args[1]
    if (
        isinstance(call.func, ast.Attribute)
        and call.func.attr in names["rename_methods"]
        and len(call.args) == 1
        and dotted not in names["rename_functions"]
    ):
        return call.func.value, call.args[0]
    return None


def check_fixed_tmp_atomic_write(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``fixed_tmp_atomic_write`` row, ordered by line."""
    row = rules.get(RULE_FIXED_TMP_ATOMIC_WRITE)
    if row is None or not row.enabled:
        return ()
    names: _Names = {
        key: frozenset(rule_strings(row, key))
        for key in (
            "rename_functions",
            "rename_methods",
            "derived_attributes",
            "neutral_names",
            "path_derivations",
        )
    }
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    issues: list[ModelValidationIssue] = []
    for _scope, nodes in _scopes(tree):
        reader = _Reader(nodes, names)
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            operands = _rename_operands(node, names)
            if operands is None or is_annotated(lines, node.lineno, marker):
                continue
            has_constant, temporary_names = reader.shape(operands[0], node.lineno)
            _, target_names = reader.shape(operands[1], node.lineno)
            path_names = temporary_names - names["neutral_names"]
            if has_constant and path_names and path_names <= target_names:
                issues.append(
                    detector_issue(row, path, lines, node.lineno, reason, remediation)
                )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_FIXED_TMP_ATOMIC_WRITE", "check_fixed_tmp_atomic_write"]
