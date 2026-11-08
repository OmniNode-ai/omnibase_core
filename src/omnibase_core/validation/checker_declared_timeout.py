# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``declared_timeout`` (OMN-23187, validators plan).

A node whose contract or overlay declares a time limit must pass a time limit to every blocking
subprocess or network call its handler makes; a declared limit that never reaches the call bounds
nothing. Facts in (one module's path and source, plus the timeout keys the node's contract and
overlays declare), ``ModelValidationIssue`` out. The blocking call names, the keyword that carries the
limit, the declaring-key pattern, the annotation marker and the reason and remediation texts are
``parameters`` of the ``declared_timeout`` rule row of ``contracts/declared_timeout.validation.yaml``;
an enabled row with a missing or mistyped parameter raises, so a broken contract fails to load
instead of passing every file. No file read, no clock, no environment.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
    parse_module,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_DECLARED_TIMEOUT = "declared_timeout"


def declared_timeout_keys(
    texts: tuple[str, ...], rules: Mapping[str, ModelValidatorRule]
) -> tuple[str, ...]:
    """The dotted key paths in ``texts`` (YAML) whose key names a limit and whose value is a number.

    A boolean, a null or a non-numeric value declares nothing. Text that does not parse as a mapping
    declares nothing.
    """
    row = rules.get(RULE_DECLARED_TIMEOUT)
    if row is None or not row.enabled:
        return ()
    pattern = re.compile(rule_string(row, "declaring_key_pattern"))
    found: list[str] = []
    for text in texts:
        try:
            loaded = load_yaml_mapping_no_duplicates(text, source="declared_timeout")
        except (yaml.YAMLError, ValueError):
            continue
        _collect(loaded, "", pattern, found)
    return tuple(found)


def _collect(
    node: object, prefix: str, pattern: re.Pattern[str], found: list[str]
) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if (
                isinstance(key, str)
                and pattern.fullmatch(key)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                found.append(path)
            _collect(value, path, pattern, found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _collect(value, f"{prefix}[{index}]", pattern, found)


def _origins(tree: ast.Module) -> dict[str, str]:
    """Local name -> dotted origin, from the module's imports (``import a.b as c``, ``from a import b``)."""
    origins: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                origins[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                origins[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return origins


def _dotted(func: ast.expr, origins: Mapping[str, str]) -> str | None:
    parts: list[str] = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if not isinstance(func, ast.Name):
        return None
    head = origins.get(func.id, func.id)
    return ".".join([head, *reversed(parts)])


def _passes_limit(call: ast.Call, keyword: str) -> bool:
    for kw in call.keywords:
        if kw.arg is None:
            return (
                True  # **kwargs may carry the limit; the checker cannot say it does not
            )
        if kw.arg == keyword:
            return not (isinstance(kw.value, ast.Constant) and kw.value.value is None)
    return False


def check_declared_timeout(
    path: Path,
    source: str,
    declared: tuple[str, ...],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the ``declared_timeout`` row, ordered by line.

    ``declared`` is the key paths the node's contract and overlays declare as a limit; with none, the
    module is judged clean.
    """
    row = rules.get(RULE_DECLARED_TIMEOUT)
    if row is None or not row.enabled:
        return ()
    blocking = frozenset(rule_strings(row, "blocking_calls"))
    keyword = rule_string(row, "timeout_keyword")
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    rule_string(row, "declaring_key_pattern")  # a missing pattern fails at load
    if not declared:
        return ()
    tree = parse_module(source)
    if tree is None:
        return ()
    lines = source.splitlines()
    origins = _origins(tree)
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func, origins)
        if name not in blocking or _passes_limit(node, keyword):
            continue
        if is_annotated(lines, node.lineno, marker):
            continue
        issues.append(
            detector_issue(
                row,
                path,
                lines,
                node.lineno,
                f"{reason} ({name}; declared {', '.join(declared)})",
                remediation,
            )
        )
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


__all__ = ["RULE_DECLARED_TIMEOUT", "check_declared_timeout", "declared_timeout_keys"]
