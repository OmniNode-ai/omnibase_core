# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Host-list rule of the hardcoded-topics validator (OMN-21503, plan task T-Q6).

A list, tuple, set or frozenset literal holding at least ``min_elements`` string
constants that each fullmatch ``element_pattern`` is a hard-coded host list: hosts
are contract or overlay data. The pattern, the minimum and the baseline path are
the rule's parameters in hardcoded_topics.validation.yaml; this module holds
none. Pure over the text it is handed, plus the CLI-result baseline step.
"""

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Callable
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_shrink_only_baseline import (
    finding_fingerprint,
    load_fingerprint_baseline,
    unbaselined_mask,
    verdict_issues,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)

__all__ = ["add_baseline_arguments", "apply_baseline_to_result", "host_list_issues"]

_FAILING = frozenset({EnumSeverity.ERROR, EnumSeverity.CRITICAL, EnumSeverity.FATAL})


def host_list_issues(
    *,
    path: Path,
    text: str,
    rule: ModelValidatorRule,
    severity: EnumSeverity,
    is_suppressed: Callable[[str], bool],
) -> list[ModelValidationIssue]:
    """One issue per host-list literal in a Python source text."""
    parameters = rule.parameters or {}
    pattern = parameters.get("element_pattern")
    minimum = parameters.get("min_elements")
    if not isinstance(pattern, str) or type(minimum) is not int or minimum < 1:
        raise ModelOnexError(
            message="Host list policy requires element_pattern and positive min_elements",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    element_pattern = re.compile(pattern)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    lines = text.splitlines()
    issues: list[ModelValidationIssue] = []
    wrappers = {
        call.args[0]: call
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "frozenset"
        and len(call.args) == 1
        and not call.keywords
        and isinstance(call.args[0], (ast.List, ast.Tuple, ast.Set))
    }
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        literal = wrappers.get(node, node)
        count = sum(
            1
            for element in node.elts
            if isinstance(element, ast.Constant)
            and isinstance(element.value, str)
            and element_pattern.fullmatch(element.value)
        )
        if count < minimum or is_suppressed(lines[literal.lineno - 1]):
            continue
        issues.append(
            ModelValidationIssue(
                severity=severity,
                message="hardcoded host list -- declare hosts in a contract or overlay",
                code=rule.rule_id,
                file_path=path,
                line_number=literal.lineno,
                rule_name=rule.rule_id,
            )
        )
    return issues


def add_baseline_arguments(parser: argparse.ArgumentParser) -> None:
    """The per-kind baseline options of a validator's CLI."""
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--previous-baseline", type=Path)


def apply_baseline_to_result(
    contract: ModelValidatorSubcontract,
    result: ModelValidationResult[None],
    args: argparse.Namespace,
    rule_id: str,
) -> ModelValidationResult[None]:
    """Grandfather the rule's findings through its shrink-only baseline."""
    rule = next((r for r in contract.rules if r.rule_id == rule_id and r.enabled), None)
    if rule is None:
        return result
    configured = (rule.parameters or {}).get("baseline_path")
    baseline_path = args.baseline or (
        Path(configured) if isinstance(configured, str) and configured else None
    )
    baseline = (
        load_fingerprint_baseline(baseline_path, rule_id)
        if baseline_path and (args.baseline or baseline_path.exists())
        else []
    )
    previous = (
        load_fingerprint_baseline(args.previous_baseline, rule_id)
        if args.previous_baseline
        else None
    )
    own = [
        i for i in result.issues if i.code == rule_id and i.file_path and i.line_number
    ]
    fingerprints = [
        finding_fingerprint(rule_id, i.file_path, i.line_number)
        for i in own
        if i.file_path and i.line_number
    ]
    mask, verdict = unbaselined_mask(rule_id, fingerprints, baseline, previous)
    kept = [i for i in result.issues if i.code != rule_id]
    kept.extend(issue for issue, new in zip(own, mask, strict=True) if new)
    kept.extend(
        verdict_issues(
            verdict.model_copy(update={"added": ()}), baseline_path=baseline_path
        )
    )
    return result.model_copy(
        update={
            "issues": kept,
            "is_valid": not any(i.severity in _FAILING for i in kept),
        }
    )
