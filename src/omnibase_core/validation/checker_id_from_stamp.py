# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``id_from_stamp`` (OMN-23189, gate OMN-21433 AC-4).

A run, row or record identity built from a wall-clock stamp that resolves to the second, with no
nonce, is shared by two events that start inside one second. Facts in (one module's path and source),
``ModelValidationIssue`` out. A finding is a name matching one of the id-name patterns (an assignment
target, a keyword argument or a string dict key) whose value is a seconds-only ``strftime`` result,
directly or through a name bound to one in the same scope, with no nonce call or nonce-named value in
the same expression. The id-name patterns, the stamp method, the second and sub-second directives, the
nonce call and name lists, the calls a stamp passes through, the annotation marker and the reason and
remediation texts are ``parameters`` of the ``id_from_stamp`` rule row of
``contracts/id_from_stamp.validation.yaml``; an enabled row with a missing or mistyped parameter raises,
so a broken contract fails to load instead of passing every file.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
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

RULE_ID_FROM_STAMP = "id_from_stamp"


@dataclass(frozen=True)
class _Vocabulary:
    """The rule row's parameters, read once."""

    name_patterns: tuple[re.Pattern[str], ...]
    stamp_method: str
    second_directives: tuple[str, ...]
    subsecond_directives: tuple[str, ...]
    nonce_calls: frozenset[str]
    nonce_fragments: tuple[str, ...]
    passthrough_calls: frozenset[str]


def _vocabulary(row: ModelValidatorRule) -> _Vocabulary:
    return _Vocabulary(
        name_patterns=tuple(
            re.compile(p) for p in rule_strings(row, "id_name_patterns")
        ),
        stamp_method=rule_string(row, "stamp_method"),
        second_directives=rule_strings(row, "second_directives"),
        subsecond_directives=rule_strings(row, "subsecond_directives"),
        nonce_calls=frozenset(rule_strings(row, "nonce_calls")),
        nonce_fragments=tuple(
            f.lower() for f in rule_strings(row, "nonce_name_fragments")
        ),
        passthrough_calls=frozenset(rule_strings(row, "passthrough_calls")),
    )


def _called_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return call.func.id if isinstance(call.func, ast.Name) else ""


def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Every node of ``scope`` without entering a nested function."""
    pending = list(ast.iter_child_nodes(scope))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pending.extend(ast.iter_child_nodes(node))


def _module_formats(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "literal"`` bindings, so a format held in a constant is read."""
    return {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def _is_second_stamp(
    call: ast.Call, vocab: _Vocabulary, formats: Mapping[str, str]
) -> bool:
    if _called_name(call) != vocab.stamp_method or not call.args:
        return False
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        fmt = arg.value
    elif isinstance(arg, ast.Name) and arg.id in formats:
        fmt = formats[arg.id]
    else:
        return False
    return any(d in fmt for d in vocab.second_directives) and not any(
        d in fmt for d in vocab.subsecond_directives
    )


def _has_nonce(expr: ast.expr, vocab: _Vocabulary) -> bool:
    for node in ast.walk(expr):
        if isinstance(node, ast.Call) and _called_name(node) in vocab.nonce_calls:
            return True
        label = node.id if isinstance(node, ast.Name) else getattr(node, "attr", "")
        if isinstance(label, str) and any(
            f in label.lower() for f in vocab.nonce_fragments
        ):
            return True
    return False


def _carries_stamp(
    expr: ast.expr,
    vocab: _Vocabulary,
    formats: Mapping[str, str],
    stamps: frozenset[str],
) -> bool:
    """Whether the value of ``expr`` is a seconds-only stamp, bare or joined into a string."""
    if isinstance(expr, ast.Name):
        return expr.id in stamps
    if isinstance(expr, ast.FormattedValue):
        return _carries_stamp(expr.value, vocab, formats, stamps)
    if isinstance(expr, ast.JoinedStr):
        return any(_carries_stamp(v, vocab, formats, stamps) for v in expr.values)
    if isinstance(expr, ast.BinOp):
        return _carries_stamp(expr.left, vocab, formats, stamps) or _carries_stamp(
            expr.right, vocab, formats, stamps
        )
    if not isinstance(expr, ast.Call):
        return False
    if _is_second_stamp(expr, vocab, formats):
        return True
    if _called_name(expr) not in vocab.passthrough_calls:
        return False
    operands = [
        *expr.args,
        *([expr.func.value] if isinstance(expr.func, ast.Attribute) else []),
    ]
    return any(_carries_stamp(a, vocab, formats, stamps) for a in operands)


def _id_sites(scope: ast.AST) -> Iterator[tuple[str, int, ast.expr]]:
    """(name, line, value) of each assignment target, keyword argument and string dict key."""
    for node in _scope_nodes(scope):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                label = (
                    target.id
                    if isinstance(target, ast.Name)
                    else getattr(target, "attr", "")
                )
                if label:
                    yield label, node.lineno, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target = node.target
            label = (
                target.id
                if isinstance(target, ast.Name)
                else getattr(target, "attr", "")
            )
            if label:
                yield label, node.lineno, node.value
        elif isinstance(node, ast.keyword) and node.arg is not None:
            yield node.arg, node.value.lineno, node.value
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    yield key.value, key.lineno, value


def _stamp_names(
    scope: ast.AST,
    vocab: _Vocabulary,
    formats: Mapping[str, str],
    inherited: frozenset[str],
) -> frozenset[str]:
    """Names bound in ``scope`` to a seconds-only stamp with no nonce, plus the enclosing scope's."""
    names = set(inherited)
    assigns = sorted(
        (n for n in _scope_nodes(scope) if isinstance(n, ast.Assign)),
        key=lambda n: n.lineno,
    )
    for node in assigns:
        if _has_nonce(node.value, vocab):
            continue
        if _carries_stamp(node.value, vocab, formats, frozenset(names)):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return frozenset(names)


def check_id_from_stamp(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``id_from_stamp`` row, ordered by line."""
    row = rules.get(RULE_ID_FROM_STAMP)
    if row is None or not row.enabled:
        return ()
    vocab = _vocabulary(row)
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    formats = _module_formats(tree)
    module_stamps = _stamp_names(tree, vocab, formats, frozenset())
    scopes: list[tuple[ast.AST, frozenset[str]]] = [(tree, module_stamps)]
    scopes.extend(
        (node, _stamp_names(node, vocab, formats, module_stamps))
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    found: dict[int, ModelValidationIssue] = {}
    for scope, stamps in scopes:
        for label, lineno, value in _id_sites(scope):
            if (
                any(p.search(label) for p in vocab.name_patterns)
                and _carries_stamp(value, vocab, formats, stamps)
                and not _has_nonce(value, vocab)
                and not is_annotated(lines, lineno, marker)
            ):
                found.setdefault(
                    lineno,
                    detector_issue(row, path, lines, lineno, reason, remediation),
                )
    return tuple(found[n] for n in sorted(found))


__all__ = ["RULE_ID_FROM_STAMP", "check_id_from_stamp"]
