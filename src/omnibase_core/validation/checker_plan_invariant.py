# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure plan-invariant checker: supplied facts and contracts in, issues out (OMN-21559)."""

from __future__ import annotations

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.plan_invariant.model_plan_invariant_check_input import (
    ModelPlanInvariantCheckInput,
)
from omnibase_core.models.plan_invariant.model_plan_invariant_check_result import (
    ModelPlanInvariantCheckResult,
)
from omnibase_core.models.plan_invariant.model_plan_invariant_rules import (
    ModelPlanInvariantRules,
)
from omnibase_core.models.task_criteria.model_task_criteria_rules import (
    ModelTaskCriteriaRules,
)
from omnibase_core.validation.checker_task_criteria import (
    block_criteria,
    criterion_has_falsifier,
    task_blocks,
)

__all__ = ["check_plan_invariant"]


def check_plan_invariant(
    request: ModelPlanInvariantCheckInput,
) -> ModelPlanInvariantCheckResult:
    """Judge task falsifiability, literal values and invariant enforcement."""
    rules = ModelPlanInvariantRules.from_contract(request.contract)
    criteria_rules = ModelTaskCriteriaRules.from_contract(
        request.task_criteria_contract
    )
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
                context={"subject": subject, **fields},
            )
        )

    invariant_row = rules.row("invariant_without_enforcing_task")
    declarations: dict[str, None] = {}
    task_lines: list[str] = []
    in_section = False
    for line in request.text.splitlines():
        if invariant_row.pattern("invariants_heading_pattern").search(line):
            in_section = True
            continue
        if in_section and invariant_row.pattern("section_end_pattern").search(line):
            in_section = False
        if in_section:
            match = invariant_row.pattern("invariant_pattern").search(line)
            if match:
                declarations[match.group(1) if match.groups() else match.group(0)] = (
                    None
                )
        else:
            task_lines.append(line)

    blocks = task_blocks("\n".join(task_lines), request.source_name, criteria_rules)
    enforced: set[str] = set()
    for task, block in blocks:
        if not any(
            criterion_has_falsifier(criterion, criteria_rules)
            for criterion in block_criteria(block, criteria_rules)
        ):
            add("task_without_falsifiable_criterion", task)

        for kind, pattern in rules.literal_kinds:
            match = pattern.search(block)
            if match:
                add("task_names_literal_value", task, kind=kind, literal=match.group(0))

        for line in block.splitlines():
            match = invariant_row.pattern("enforces_pattern").search(line)
            if match:
                ids = match.group(1) if match.groups() else match.group(0)
                enforced.update(
                    item.group(0)
                    for item in invariant_row.pattern("id_pattern").finditer(ids)
                )

    for invariant in declarations:
        if invariant not in enforced:
            add("invariant_without_enforcing_task", invariant)

    return ModelPlanInvariantCheckResult(
        issues=tuple(issues),
        exit_code=1
        if any(issue.severity.is_error_or_above() for issue in issues)
        else 0,
        task_count=len(blocks),
        invariant_count=len(declarations),
    )
