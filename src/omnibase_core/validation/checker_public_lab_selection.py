# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker: a public-repository workflow selects no lab runner (OMN-19998).

RULING 2026-11-05T09:10:44Z orders it made impossible. A workflow in a public
repository is refused when a job's ``runs-on`` names a label that is not
GitHub-hosted, reads a variable that is not a declared hosted seam, or reads a
value the workflow cannot prove hosted, unless a typed route says what replaces
that job. A job that calls a reusable workflow a route records is refused the
same way, and a seam variable whose live value is not hosted is refused.

This check does not stop a fork pull request that edits its own workflow file:
that job runs before any merge gate. Only the runner group refusing public
repositories does that. This check stops the merge.

Facts in (repository, visibility, workflow sources, routes, variables),
``ModelValidationIssue`` out: no file read, no clock, no environment. Every
pattern, name list and remediation text is a ``parameters`` entry of the rule
rows in ``contracts/public_lab_selection.validation.yaml``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import yaml

from omnibase_core.enums.enum_public_lab_route_kind import EnumPublicLabRouteKind
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.version_drift.model_public_lab_node_routes import (
    ModelPublicLabNodeRoutes,
)
from omnibase_core.models.version_drift.model_public_lab_selection_input import (
    ModelPublicLabSelectionInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
    rule_strings,
)

RULE_LAB_SELECTED = "lab_selected_in_public"
RULE_REUSABLE_CALLER = "lab_reusable_caller"
RULE_SEAM_VALUE = "seam_value_not_hosted"
RULE_ROUTE_ADDED = "route_added"
RULE_ROUTE_STALE = "route_stale"
RULE_UNPARSEABLE = "workflow_does_not_parse"


@cache
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def _hosted(label: object, row: ModelValidatorRule) -> bool:
    pattern = _re(rule_string(row, "hosted_label_pattern"))
    return isinstance(label, str) and bool(pattern.match(label.strip()))


def _closing_paren(text: str, start: int) -> int | None:
    depth = 0
    quoted = False
    for index in range(start, len(text)):
        char = text[index]
        if char == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _private_guarded(body: str, row: ModelValidatorRule) -> bool:
    """True for ``<private guard> (<route>) || <hosted>``: a public repository never takes the route."""
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


def _strip_seam_references(body: str, row: ModelValidatorRule) -> str:
    """The expression with each declared hosted seam reference removed."""
    seams = rule_strings(row, "hosted_seam_variables")

    def replace(match: re.Match[str]) -> str:
        return "''" if match.group(1) in seams else match.group(0)

    return _re(rule_string(row, "variable_reference_pattern")).sub(replace, body)


def _expression_selection(expression: str, row: ModelValidatorRule) -> str | None:
    """The kind of lab selection in one ``${{ }}`` expression, or None when proved hosted."""
    body = expression.strip()
    if not (body.startswith("${{") and body.endswith("}}")):
        return "computed"
    body = body[3:-2].strip()
    if _private_guarded(body, row):
        return None
    stripped = _strip_seam_references(body, row)
    if rule_string(row, "self_hosted_marker") in stripped.lower():
        return "lab_label"
    if _re(rule_string(row, "unprovable_context_pattern")).search(stripped):
        return "computed"
    stripped = _re(rule_string(row, "non_label_call_pattern")).sub("(", stripped)
    arrays = _re(rule_string(row, "json_array_literal_pattern")).findall(stripped)
    for array in arrays:
        if not all(_hosted(item, row) for item in re.findall(r'"([^"]*)"', array)):
            return "lab_label"
    literals = _re(rule_string(row, "returned_literal_pattern")).findall(stripped)
    return None if all(_hosted(item, row) for item in literals) else "lab_label"


def _matrix_values(job: Mapping[object, object], key: str) -> object:
    strategy = job.get("strategy")
    matrix = strategy.get("matrix") if isinstance(strategy, Mapping) else None
    return matrix.get(key) if isinstance(matrix, Mapping) else None


def job_selection(job: Mapping[object, object], row: ModelValidatorRule) -> str | None:
    """``lab_label``, ``computed`` or ``runner_group`` when a job can leave GitHub-hosted; else None."""
    return _selection(job.get("runs-on"), job, row)


def _selection(
    runs_on: object,
    job: Mapping[object, object],
    row: ModelValidatorRule,
) -> str | None:
    if isinstance(runs_on, str):
        if "${{" not in runs_on:
            return None if _hosted(runs_on, row) else "lab_label"
        reference = _re(rule_string(row, "matrix_reference_pattern")).match(
            runs_on.strip()
        )
        if reference is not None:
            values = _matrix_values(job, reference.group(1))
            if isinstance(values, list) and values:
                return _selection(values, job, row)
        return _expression_selection(runs_on, row)
    if isinstance(runs_on, list):
        for label in runs_on:
            kind = _selection(label, job, row)
            if kind is not None:
                return kind
        return None
    if isinstance(runs_on, Mapping):
        if "group" in runs_on:
            return "runner_group"
        return _selection(runs_on.get("labels", []), job, row)
    return None


def _callee(
    uses: str,
    caller_repository: str,
    row: ModelValidatorRule,
) -> tuple[str, str] | None:
    match = _re(rule_string(row, "uses_pattern")).match(uses.strip())
    if match is None:
        return None
    return (match.group("repo") or caller_repository, match.group("path"))


def _judge_file(
    source: str,
    path: str,
    request: ModelPublicLabSelectionInput,
    rules: Mapping[str, ModelValidatorRule],
) -> list[ModelValidationIssue]:
    document = load_yaml_mapping_no_duplicates(source, source=path)
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping):
        return []
    routed = request.routes.keys()
    lab_callees = {
        (route.repository, route.workflow)
        for route in request.routes.routes
        if route.kind is not EnumPublicLabRouteKind.MOVES_TO_HOSTED
    }
    issues: list[ModelValidationIssue] = []
    selecting: set[str] = set()
    for job_id, job in jobs.items():
        if not isinstance(job, Mapping):
            continue
        name = str(job_id)
        key = (request.repository, path, name)
        kind = job_selection(job, rules[RULE_LAB_SELECTED])
        if kind is not None:
            selecting.add(name)
            if key not in routed and rules[RULE_LAB_SELECTED].enabled:
                issues.append(
                    _issue(
                        rules[RULE_LAB_SELECTED],
                        path,
                        f"{path}:jobs.{name}: {kind} runs-on in public repository "
                        f"{request.repository} (rule {RULE_LAB_SELECTED})",
                        {"job": name, "kind": kind},
                    )
                )
        uses = job.get("uses")
        if isinstance(uses, str) and rules[RULE_REUSABLE_CALLER].enabled:
            callee = _callee(uses, request.repository, rules[RULE_REUSABLE_CALLER])
            if callee in lab_callees and key not in routed:
                issues.append(
                    _issue(
                        rules[RULE_REUSABLE_CALLER],
                        path,
                        f"{path}:jobs.{name}: calls {callee[1]} of {callee[0]}, which a "
                        f"typed route records as selecting the lab "
                        f"(rule {RULE_REUSABLE_CALLER})",
                        {"job": name},
                    )
                )
            if callee in lab_callees:
                selecting.add(name)
    if rules[RULE_ROUTE_STALE].enabled:
        issues.extend(
            _issue(
                rules[RULE_ROUTE_STALE],
                path,
                f"{path}:jobs.{route.job}: the route no longer matches a job selecting "
                f"the lab; remove it so the count falls (rule {RULE_ROUTE_STALE})",
                {"job": route.job},
            )
            for route in request.routes.routes
            if route.repository == request.repository
            and route.workflow == path
            and route.job not in selecting
        )
    return issues


def check_seam_values(
    request: ModelPublicLabSelectionInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for each declared hosted seam variable whose live value is not hosted."""
    if not request.public or not rules[RULE_SEAM_VALUE].enabled:
        return ()
    selected = rules[RULE_LAB_SELECTED]
    issues: list[ModelValidationIssue] = []
    for name in rule_strings(selected, "hosted_seam_variables"):
        value = request.variables.get(name)
        if not value:
            continue
        try:
            labels = json.loads(value)
        except ValueError:
            labels = None
        if (
            isinstance(labels, list)
            and labels
            and all(_hosted(label, selected) for label in labels)
        ):
            continue
        issues.append(
            _issue(
                rules[RULE_SEAM_VALUE],
                name,
                f"{name}: live value {value!r} in public repository "
                f"{request.repository} is not a GitHub-hosted label set "
                f"(rule {RULE_SEAM_VALUE})",
                {"variable": name},
            )
        )
    return tuple(issues)


def check_public_lab_selection(
    request: ModelPublicLabSelectionInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for each public-repository job selecting the lab without a typed route."""
    if not request.public:
        return ()
    issues: list[ModelValidationIssue] = []
    for file in request.files:
        try:
            issues.extend(_judge_file(file.source, file.path, request, rules))
        except (yaml.YAMLError, ValueError) as exc:
            if rules[RULE_UNPARSEABLE].enabled:
                issues.append(
                    _issue(
                        rules[RULE_UNPARSEABLE],
                        file.path,
                        f"{file.path}: workflow does not parse: {exc}",
                    )
                )
    return tuple(issues)


def check_routes_only_shrink(
    base: ModelPublicLabNodeRoutes,
    head: ModelPublicLabNodeRoutes,
    rules: Mapping[str, ModelValidatorRule],
    path: str,
) -> tuple[ModelValidationIssue, ...]:
    """Issues for each route ``head`` has that the base revision does not."""
    if not rules[RULE_ROUTE_ADDED].enabled:
        return ()
    return tuple(
        _issue(
            rules[RULE_ROUTE_ADDED],
            path,
            f"{key[0]}:{key[1]}:jobs.{key[2]}: route not in the base revision; the "
            f"list only shrinks (rule {RULE_ROUTE_ADDED})",
            {"job": key[2]},
        )
        for key in sorted(head.keys() - base.keys())
    )


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
    "RULE_LAB_SELECTED",
    "RULE_REUSABLE_CALLER",
    "RULE_ROUTE_ADDED",
    "RULE_ROUTE_STALE",
    "RULE_SEAM_VALUE",
    "RULE_UNPARSEABLE",
    "check_public_lab_selection",
    "check_routes_only_shrink",
    "check_seam_values",
    "job_selection",
]
