# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure collaborator-lane predicate over lane briefs, proof rules and placements (OMN-21599).

Operator ruling 2026-10-30T12:43:03Z: collaborators build, test and prove on the
test/stability lane and never depend on the dev lane. Facts in, issues out: the
document text and its name arrive in the request. Every pattern, key list and
diagnostic comes from the supplied subcontract.
"""

from __future__ import annotations

from collections.abc import Iterator

import yaml

from omnibase_core.models.collaborator_lane.model_collaborator_lane_check_input import (
    ModelCollaboratorLaneCheckInput,
)
from omnibase_core.models.collaborator_lane.model_collaborator_lane_check_result import (
    ModelCollaboratorLaneCheckResult,
)
from omnibase_core.models.collaborator_lane.model_collaborator_lane_rules import (
    ModelCollaboratorLaneRules,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.task_criteria.model_task_criteria_rule_row import (
    ModelTaskCriteriaRuleRow,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["check_collaborator_lane", "text_outside_block"]


def text_outside_block(text: str, start: str, end: str, newline: str = "") -> str:
    """The text with the pasted standing block removed, which every brief carries verbatim."""
    flat = text.replace(newline, "\n") if newline else text
    begin = flat.find(start)
    if begin < 0:
        return flat
    stop = flat.find(end, begin)
    if stop < 0:
        return flat
    return flat[:begin] + flat[stop + len(end) :]


def _scalars(value: object) -> Iterator[str]:
    """Every string a placement value names, whether it is one string or a list of them."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _scalars(item)


def _mappings(node: object) -> Iterator[dict[object, object]]:
    """Every mapping of a parsed YAML document, nested ones included."""
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from _mappings(child)
    elif isinstance(node, list):
        for child in node:
            yield from _mappings(child)


def _dev_placements(
    document: dict[object, object], row: ModelTaskCriteriaRuleRow
) -> list[tuple[str, str]]:
    """(role, lane value) of each mapping that gives a collaborator role a dev-lane value."""
    role_pattern = row.pattern("collaborator_role_pattern")
    value_pattern = row.pattern("dev_lane_value_pattern")
    found: list[tuple[str, str]] = []
    for mapping in _mappings(document):
        roles = [
            role
            for key in row.lists["role_keys"]
            for role in _scalars(mapping.get(key))
            if role_pattern.search(role)
        ]
        if not roles:
            continue
        for key in row.lists["lane_keys"]:
            found.extend(
                (roles[0], value)
                for value in _scalars(mapping.get(key))
                if value_pattern.fullmatch(value)
            )
    return found


def check_collaborator_lane(
    request: ModelCollaboratorLaneCheckInput,
) -> ModelCollaboratorLaneCheckResult:
    """Judge one document using only the supplied facts and contract."""
    rules = ModelCollaboratorLaneRules.from_contract(request.contract)
    issues: list[ModelValidationIssue] = []

    def add(code: str, subject: str, **fields: str) -> None:
        row = rules.row(code)
        issues.append(
            ModelValidationIssue(
                severity=row.severity,
                message=row.message.format(subject=subject, **fields),
                code=code,
                rule_name=code,
                context={"subject": subject},
            )
        )

    def judges(code: str) -> bool:
        row = rules.row(code)
        return row.enabled and row.judges(request.source_name)

    for code in ("brief_on_dev_lane", "brief_without_collaborator_lane"):
        if not judges(code):
            continue
        row = rules.row(code)
        outside = text_outside_block(
            request.text,
            row.texts["block_start"],
            row.texts["block_end"],
            row.texts["escaped_newline"],
        )
        if not row.pattern("collaborator_pattern").search(outside):
            continue
        if code == "brief_on_dev_lane":
            target = row.pattern("dev_lane_pattern").search(outside)
            if target:
                add(code, request.source_name, target=target.group(0))
        elif not row.pattern("assigned_lane_pattern").search(outside):
            add(code, request.source_name)

    if judges("proof_rule_on_dev_lane"):
        row = rules.row("proof_rule_on_dev_lane")
        for paragraph in row.pattern("paragraph_break_pattern").split(request.text):
            target = row.pattern("dev_lane_pattern").search(paragraph)
            if (
                target
                and row.pattern("collaborator_pattern").search(paragraph)
                and row.pattern("proof_pattern").search(paragraph)
                and not row.pattern("assigned_lane_pattern").search(paragraph)
            ):
                add(
                    "proof_rule_on_dev_lane",
                    request.source_name,
                    target=target.group(0),
                    excerpt=" ".join(paragraph.split())[:80],
                )

    if judges("placement_on_dev_lane"):
        row = rules.row("placement_on_dev_lane")
        try:
            document = load_yaml_mapping_no_duplicates(
                request.text, source=request.source_name
            )
        except (yaml.YAMLError, ValueError) as exc:
            if rules.row("placement_unreadable").enabled:
                add("placement_unreadable", request.source_name, reason=str(exc)[:80])
        else:
            for role, lane in _dev_placements(document, row):
                add("placement_on_dev_lane", request.source_name, role=role, lane=lane)

    return ModelCollaboratorLaneCheckResult(
        issues=tuple(issues),
        exit_code=1
        if any(issue.severity.is_error_or_above() for issue in issues)
        else 0,
    )
