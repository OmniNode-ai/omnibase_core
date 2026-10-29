# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker: no public-repository job runs on the fleet (OMN-19998, OMN-21280, OMN-21503).

RULING 2026-10-16T07:07:09Z: "Ci runners should be for private repos only."
In a PUBLIC repository this checker refuses every job whose ``runs-on`` is, or
can resolve to, anything but a GitHub-hosted label: a literal label that is not
hosted, and a computed ``runs-on`` expression that names such a label or reads a
value the workflow cannot prove hosted. There is no baseline (OMN-21280). One
computed shape is proved hosted for a public repository: the private-caller
guard whose parenthesized route only a private repository can take. A private
repository passes. Jobs that call a reusable workflow with ``uses:`` carry no
``runs-on`` and are judged where the callee is defined.

Facts in (repository, visibility, workflow sources), ``ModelValidationIssue`` out:
no file read, no clock, no environment. Every pattern, marker and the remediation
text are ``parameters`` of the rule rows in
``contracts/public_runner_placement.validation.yaml``; this module holds none.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
)

RULE_SELF_HOSTED = "self_hosted_in_public"
RULE_UNPARSEABLE = "workflow_does_not_parse"


@cache
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def _hosted(label: object, row: ModelValidatorRule) -> bool:
    pattern = _re(rule_string(row, "hosted_label_pattern"))
    return isinstance(label, str) and bool(pattern.match(label.strip()))


def _closing_paren(text: str, start: int) -> int | None:
    """Index of the ``)`` matching the ``(`` at ``start``; quoted text is skipped."""
    depth = 0
    quoted = False
    for index in range(start, len(text)):
        char = text[index]
        if char == "'":
            quoted = not quoted  # `''` inside a string toggles twice: no change
        elif quoted:
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _private_guarded(expression: str, row: ModelValidatorRule) -> bool:
    """True for ``${{ <private guard> (<route>) || <hosted> }}``.

    For a public repository the guard is false, so the expression is the hosted
    fallback whatever ``<route>`` reads. The route must be one parenthesized
    group, or an inner ``||`` would bind outside the guard.
    """
    body = expression.strip()
    if not (body.startswith("${{") and body.endswith("}}")):
        return False
    body = body[3:-2].strip()
    guard = _re(rule_string(row, "private_guard_pattern")).match(body)
    if guard is None:
        return False
    end = _closing_paren(body, guard.end() - 1)
    if end is None:
        return False
    fallback = _re(rule_string(row, "hosted_fallback_pattern")).match(
        body[end + 1 :].strip()
    )
    if fallback is None:
        return False
    label, array = fallback.groups()
    if label is not None:
        return _hosted(label, row)
    labels = re.findall(r'"([^"]*)"', array)
    return bool(labels) and all(_hosted(item, row) for item in labels)


def _computed_is_unproven(expression: str, row: ModelValidatorRule) -> bool:
    """True when a ``runs-on`` expression can resolve to a non-hosted label."""
    if _private_guarded(expression, row):
        return False
    if (
        _re(rule_string(row, "unprovable_context_pattern")).search(expression)
        or rule_string(row, "self_hosted_marker") in expression.lower()
    ):
        return True
    literals = _re(rule_string(row, "returned_literal_pattern")).findall(expression)
    for array in _re(rule_string(row, "json_array_literal_pattern")).findall(
        expression
    ):
        literals.extend(re.findall(r'"([^"]*)"', array))
    return any(not _hosted(literal, row) for literal in literals)


def runs_on_kind(runs_on: object, row: ModelValidatorRule) -> str | None:
    """``self_hosted_label`` or ``computed`` when ``runs-on`` can leave GitHub-hosted; else None."""
    if isinstance(runs_on, str):
        if "${{" in runs_on:
            return "computed" if _computed_is_unproven(runs_on, row) else None
        return None if _hosted(runs_on, row) else "self_hosted_label"
    if isinstance(runs_on, list):
        for label in runs_on:
            kind = runs_on_kind(label, row)
            if kind is not None:
                return kind
        return None
    if isinstance(runs_on, Mapping):
        if "group" in runs_on:
            return "self_hosted_label"
        return runs_on_kind(runs_on.get("labels", []), row)
    return None


def self_hosted_jobs(source: str, path: str, row: ModelValidatorRule) -> dict[str, str]:
    """Job id to kind for each job of a workflow that can leave GitHub-hosted runners.

    Invalid YAML raises ``yaml.YAMLError`` or ``ValueError``.
    """
    document = load_yaml_mapping_no_duplicates(source, source=path)
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping):
        return {}
    found: dict[str, str] = {}
    for job_id, job in jobs.items():
        if not isinstance(job, Mapping) or "runs-on" not in job:
            continue
        kind = runs_on_kind(job["runs-on"], row)
        if kind is not None:
            found[str(job_id)] = kind
    return found


def check_public_runner_placement(
    request: ModelPublicRunnerPlacementInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for each public-repository job that can run on a self-hosted runner."""
    if not request.public or not rules[RULE_SELF_HOSTED].enabled:
        return ()
    issues: list[ModelValidationIssue] = []
    for file in request.files:
        try:
            jobs = self_hosted_jobs(file.source, file.path, rules[RULE_SELF_HOSTED])
        except (yaml.YAMLError, ValueError) as exc:
            if rules[RULE_UNPARSEABLE].enabled:
                issues.append(
                    _issue(
                        rules[RULE_UNPARSEABLE],
                        file.path,
                        f"{file.path}: workflow does not parse: {exc}",
                    )
                )
            continue
        issues.extend(
            _issue(
                rules[RULE_SELF_HOSTED],
                file.path,
                f"{file.path}:jobs.{job}: {kind} runs-on in public repository "
                f"{request.repository} (rule {RULE_SELF_HOSTED})",
                {"job": job, "kind": kind},
            )
            for job, kind in sorted(jobs.items())
        )
    return tuple(issues)


def _issue(
    row: ModelValidatorRule,
    path: str,
    message: str,
    context: dict[str, str] | None = None,
) -> ModelValidationIssue:
    remediation = (row.parameters or {}).get("remediation")
    return ModelValidationIssue(
        severity=row.severity,
        message=message,
        code=row.rule_id,
        file_path=Path(path),
        rule_name=row.rule_id,
        suggestion=remediation if isinstance(remediation, str) else None,
        context=context,
    )


__all__ = [
    "RULE_SELF_HOSTED",
    "RULE_UNPARSEABLE",
    "check_public_runner_placement",
    "runs_on_kind",
    "self_hosted_jobs",
]
