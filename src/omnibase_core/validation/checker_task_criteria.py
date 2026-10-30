# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure task-criteria predicate over plan tasks, tickets and lane briefs (OMN-21535).

Facts in, issues out: the document text, its name and the repository lifecycle facts
arrive in the request. Every pattern, name list, digest, level and diagnostic comes from
the supplied subcontract.
"""

from __future__ import annotations

import hashlib
import re

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.task_criteria.model_task_criteria_check_input import (
    ModelTaskCriteriaCheckInput,
)
from omnibase_core.models.task_criteria.model_task_criteria_check_result import (
    ModelTaskCriteriaCheckResult,
)
from omnibase_core.models.task_criteria.model_task_criteria_rules import (
    ModelTaskCriteriaRules,
)

__all__ = [
    "block_criteria",
    "check_task_criteria",
    "criterion_has_falsifier",
    "task_blocks",
]


def task_blocks(
    text: str, source_name: str, rules: ModelTaskCriteriaRules
) -> list[tuple[str, str]]:
    """Split the text into (task id, block text); a text without headings is one task."""
    heading = rules.row("missing_configuration_criterion").pattern(
        "task_heading_pattern"
    )
    lines = text.splitlines()
    starts = [
        (index, match.group(1) if match.groups() else match.group(0))
        for index, line in enumerate(lines)
        if (match := heading.search(line))
    ]
    if not starts:
        return [(source_name, text)]
    ends = [index for index, _ in starts[1:]] + [len(lines)]
    return [
        (task, "\n".join(lines[begin:end]))
        for (begin, task), end in zip(starts, ends, strict=True)
    ]


def block_criteria(block: str, rules: ModelTaskCriteriaRules) -> list[str]:
    """Criterion bullets of a block, each with its indented continuation lines."""
    criterion = rules.row("missing_configuration_criterion").pattern(
        "criterion_pattern"
    )
    found: list[str] = []
    open_item = False
    for line in block.splitlines():
        if criterion.search(line):
            found.append(line.strip())
            open_item = True
        elif open_item and line.startswith((" ", "\t")) and line.strip():
            found[-1] += " " + line.strip()
        else:
            open_item = False
    return found


def criterion_has_falsifier(criterion: str, rules: ModelTaskCriteriaRules) -> bool:
    """Whether a criterion names a falsifier action and an observable result."""
    row = rules.row("criterion_without_falsifier")
    match = row.pattern("falsifier_pattern").search(criterion)
    said = match.group(1) if match and match.groups() else ""
    return bool(
        said
        and row.pattern("action_pattern").search(said)
        and row.pattern("observable_pattern").search(said)
    )


def _rule_block(text: str, start: str, end: str, newline: str = "") -> str | None:
    """The standing block between its first and last marker, or None when absent."""
    flat = text.replace(newline, "\n") if newline else text
    begin = flat.find(start)
    if begin < 0:
        return None
    stop = flat.find(end, begin)
    if stop < 0:
        return None
    return flat[begin : stop + len(end)]


def check_task_criteria(
    request: ModelTaskCriteriaCheckInput,
) -> ModelTaskCriteriaCheckResult:
    """Judge one document using only the supplied facts and contract."""
    rules = ModelTaskCriteriaRules.from_contract(request.contract)
    issues: list[ModelValidationIssue] = []

    def add(code: str, subject: str, **fields: str) -> None:
        row = rules.row(code)
        if not row.enabled or not row.judges(request.source_name):
            return
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

    config_row = rules.row("missing_configuration_criterion")
    blocks = task_blocks(request.text, request.source_name, rules)
    for task, block in blocks:
        criteria = block_criteria(block, rules)
        if not any(
            config_row.pattern("configuration_pattern").search(c) for c in criteria
        ):
            add("missing_configuration_criterion", task)
        bindings = [
            c
            for c in criteria
            if rules.row("missing_bindings_criterion")
            .pattern("bindings_pattern")
            .search(c)
        ]
        if not bindings:
            add("missing_bindings_criterion", task)

        fal = rules.row("criterion_without_falsifier")
        for criterion in criteria:
            if not criterion_has_falsifier(criterion, rules):
                add("criterion_without_falsifier", task, criterion=criterion[:80])

        overlay = rules.row("missing_two_overlay_falsifier")
        if overlay.pattern("applies_pattern").search(block) and not any(
            overlay.pattern("in_memory_pattern").search(c)
            and overlay.pattern("broker_pattern").search(c)
            and overlay.pattern("no_code_change_pattern").search(c)
            for c in criteria
        ):
            add("missing_two_overlay_falsifier", task)

        replay = rules.row("replay_only_bindings_falsifier")
        for criterion in bindings:
            match = fal.pattern("falsifier_pattern").search(criterion)
            said = match.group(1) if match and match.groups() else ""
            if replay.pattern("replay_only_pattern").search(
                said
            ) and not replay.pattern("live_evidence_pattern").search(said):
                add("replay_only_bindings_falsifier", task)

        zero = rules.row("missing_zero_literal_falsifier")
        if zero.pattern("applies_pattern").search(block) and not any(
            zero.pattern("zero_pattern").search(c)
            and all(name in c for name in zero.lists["validator_names"])
            for c in criteria
        ):
            add("missing_zero_literal_falsifier", task)

        resolution = rules.row("missing_container_resolution_criterion")
        if resolution.pattern("applies_pattern").search(block) and not any(
            resolution.pattern("resolution_pattern").search(c) for c in criteria
        ):
            add("missing_container_resolution_criterion", task)

        frozen = rules.row("task_in_frozen_repository")
        for files in frozen.pattern("files_pattern").findall(block):
            for repository in frozen.pattern("repository_pattern").findall(files):
                state = request.repository_lifecycle.get(repository)
                if state is None or state not in frozen.lists["frozen_states"]:
                    continue
                permitted = bool(frozen.pattern("release_pattern").search(block)) or (
                    state in frozen.lists["fix_permitted_states"]
                    and bool(frozen.pattern("fix_pattern").search(block))
                )
                if not permitted:
                    add(
                        "task_in_frozen_repository",
                        task,
                        repository=repository,
                        state=state,
                    )

    if judges("brief_missing_rule_block"):
        brief = rules.row("brief_missing_rule_block")
        standing = _rule_block(
            request.text,
            brief.texts["block_start"],
            brief.texts["block_end"],
            brief.texts["escaped_newline"],
        )
        digest = hashlib.sha256(" ".join((standing or "").split()).encode()).hexdigest()
        if standing is None or digest not in brief.lists["accepted_digests"]:
            add("brief_missing_rule_block", request.source_name, digest=digest)

    if judges("rule_block_incomplete"):
        incomplete = rules.row("rule_block_incomplete")
        scope = (
            _rule_block(
                request.text,
                incomplete.texts["block_start"],
                incomplete.texts["block_end"],
            )
            or ""
        )
        missing = [
            item
            for item in incomplete.lists["required_items"]
            if not re.search(item, scope)
        ]
        if missing:
            add("rule_block_incomplete", request.source_name, items="; ".join(missing))

    return ModelTaskCriteriaCheckResult(
        issues=tuple(issues),
        exit_code=1
        if any(issue.severity.is_error_or_above() for issue in issues)
        else 0,
        task_count=len(blocks),
    )
