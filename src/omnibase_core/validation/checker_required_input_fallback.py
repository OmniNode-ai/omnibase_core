# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``required_input_fallback`` (OMN-24538, fail-open ratchets).

A node whose contract declares an input ``required`` must not answer that input's absence with a
made-up value: a ``get`` with a default, a three-argument ``getattr``, an ``or`` over a literal, or
an ``except`` whose body returns a literal all let the handler carry on as if the input had
arrived. Facts in (one module's path and source, plus the input names the node's contract marks
required), ``ModelValidationIssue`` out. The contract file name, the ``get`` and ``getattr``
method names, the annotation marker and the reason and remediation texts are ``parameters`` of the
``required_input_fallback`` rule row of ``contracts/required_input_fallback.validation.yaml``; an
enabled row with a missing or mistyped parameter raises, so a broken contract fails to load
instead of passing every file. No file read, no clock, no environment; a module that does not
parse, or a contract text that does not parse as a mapping, raises instead of being judged clean.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    dotted_name,
    is_annotated,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_REQUIRED_INPUT_FALLBACK = "required_input_fallback"

_INPUTS_KEY = "inputs"
_REQUIRED_KEY = "required"


def required_inputs(contract_text: str) -> tuple[str, ...]:
    """The input names ``contract_text`` marks ``required: true`` (a boolean; the string is not).

    Every ``inputs`` mapping in the contract counts, so a flow nested under a step declares too.
    Text that does not parse, or that parses to something other than a mapping, raises: a damaged
    contract must stop the validator instead of passing every handler clean.
    """
    try:
        loaded = load_yaml_mapping_no_duplicates(
            contract_text, source=RULE_REQUIRED_INPUT_FALLBACK
        )
    except (yaml.YAMLError, ValueError) as exc:
        raise ModelOnexError(
            message=(
                f"{RULE_REQUIRED_INPUT_FALLBACK}: the node contract does not parse as a "
                f"mapping: {exc}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    found: list[str] = []
    _collect(loaded, found)
    return tuple(dict.fromkeys(found))


def _collect(node: object, found: list[str]) -> None:
    """Gather the ``required: true`` entry names of every ``inputs`` mapping under ``node``."""
    if isinstance(node, Mapping):
        for key, value in node.items():
            if key == _INPUTS_KEY and isinstance(value, Mapping):
                for name, spec in value.items():
                    if (
                        isinstance(name, str)
                        and isinstance(spec, Mapping)
                        and spec.get(_REQUIRED_KEY) is True
                    ):
                        found.append(name)
            _collect(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect(item, found)


def _required_name(node: ast.expr, names: frozenset[str]) -> str | None:
    """The required input a plain ``x.name`` or ``x["name"]`` access reads, if it is one."""
    if isinstance(node, ast.Attribute):
        return node.attr if node.attr in names else None
    if isinstance(node, ast.Subscript):
        index = node.slice
        if (
            isinstance(index, ast.Constant)
            and isinstance(index.value, str)
            and index.value in names
        ):
            return index.value
    return None


def _default_literal(node: ast.expr) -> bool:
    """Whether ``node`` is a constant or an empty container: a made-up answer, not a computed one."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return not node.elts
    return isinstance(node, ast.Dict) and not node.keys


def _literal_return(line: ast.Return | None) -> bool:
    """Whether ``line`` returns a constant or a container of constants (``return None`` counts)."""
    if line is None or line.value is None:
        return False
    if isinstance(line.value, ast.Constant):
        return True
    if isinstance(line.value, (ast.List, ast.Tuple, ast.Set)):
        return all(isinstance(e, ast.Constant) for e in line.value.elts)
    if isinstance(line.value, ast.Dict):
        return all(
            isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
            for k, v in zip(line.value.keys, line.value.values, strict=True)
        )
    return False


def _exception_label(handler: ast.ExceptHandler) -> str:
    """The handler's caught exception as text, or ``bare`` for a handler that names none."""
    if handler.type is None:
        return "bare"
    return dotted_name(handler.type) or "<exception>"


def check_required_input_fallback(
    path: Path,
    source: str,
    required: tuple[str, ...],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``required_input_fallback`` row, ordered by line.

    ``required`` is the input names the node's contract marks required; with none, the module is
    judged clean. Source that does not parse raises: a broken module must stop the validator
    instead of slipping past the refusal unread.
    """
    row = rules.get(RULE_REQUIRED_INPUT_FALLBACK)
    if row is None or not row.enabled:
        return ()
    get_methods = frozenset(rule_strings(row, "get_methods"))
    getattr_names = frozenset(rule_strings(row, "getattr_names"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    rule_string(row, "contract_file")  # a missing contract_file fails at load
    if not required:
        return ()
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        raise ModelOnexError(
            message=f"{RULE_REQUIRED_INPUT_FALLBACK}: {path}: the module does not parse: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    names = frozenset(required)
    lines = source.splitlines()
    issues: list[ModelValidationIssue] = []

    def refuse(lineno: int, detail: str) -> None:
        if not is_annotated(lines, lineno, marker):
            issues.append(
                detector_issue(
                    row,
                    path,
                    lines,
                    lineno,
                    f"{reason} ({detail}; required {', '.join(sorted(names))})",
                    remediation,
                )
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in get_methods
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value in names
            ):
                name = node.args[0].value
                receiver = dotted_name(func.value) or "<receiver>"
                refuse(node.lineno, f'{receiver}.{func.attr}("{name}", ...)')
            elif (
                isinstance(func, ast.Name)
                and func.id in getattr_names
                and len(node.args) == 3
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and node.args[1].value in names
            ):
                refuse(node.lineno, f'{func.id}(..., "{node.args[1].value}", ...)')
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            or_name = _required_name(node.values[0], names)
            if or_name is None or not any(
                _default_literal(value) for value in node.values[1:]
            ):
                continue
            access = node.values[0]
            receiver = dotted_name(
                access.value
                if isinstance(access, (ast.Attribute, ast.Subscript))
                else access
            )
            receiver = receiver or "<receiver>"
            if isinstance(access, ast.Attribute):
                shown = f"{receiver}.{or_name}"
            else:
                shown = f'{receiver}["{or_name}"]'
            refuse(node.lineno, f"{shown} or a literal default")
        elif isinstance(node, ast.ExceptHandler):
            body = [n for stmt in node.body for n in ast.walk(stmt)]
            returned = next(
                (n for n in body if isinstance(n, ast.Return) and _literal_return(n)),
                None,
            )
            if returned is None or any(isinstance(n, ast.Raise) for n in body):
                continue
            refuse(
                returned.lineno,
                f"except {_exception_label(node)} returns a literal default",
            )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = [
    "RULE_REQUIRED_INPUT_FALLBACK",
    "check_required_input_fallback",
    "required_inputs",
]
