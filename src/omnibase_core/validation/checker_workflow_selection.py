# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Workflow selection and parity rule data of the merge-queue parity check (OMN-21503, OMN-21518)."""

from __future__ import annotations

import re
from functools import cache
from importlib import resources

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_rules import (
    ModelMergeQueueParityRules,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = [
    "is_workflow",
    "load_parity_contract",
    "load_parity_rules",
    "load_workflow_rule",
    "parity_rules_from_contract",
]


@cache
def load_parity_contract() -> ModelValidatorSubcontract:
    """The packaged ``merge_queue_parity`` validator contract."""
    raw = resources.files("omnibase_core.validation").joinpath(
        "contracts/merge_queue_parity.validation.yaml"
    )
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelValidatorSubcontract)


def _rows(contract: ModelValidatorSubcontract) -> dict[str, ModelValidatorRule]:
    return {row.rule_id: row for row in contract.rules}


def _row(rows: dict[str, ModelValidatorRule], rule_id: str) -> ModelValidatorRule:
    if rule_id not in rows:
        raise ModelOnexError(
            message=f"merge_queue_parity contract has no rule row {rule_id!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return rows[rule_id]


def load_workflow_rule() -> ModelValidatorRule:
    """Load workflow selection data shipped with the package."""
    return _row(_rows(load_parity_contract()), "workflow_path")


def is_workflow(path: str, *, rule: ModelValidatorRule | None = None) -> bool:
    """True for a workflow selected by the packaged rule's path pattern."""
    row = load_workflow_rule() if rule is None else rule
    return bool(re.match(rule_string(row, "path_pattern"), path))


def parity_rules_from_contract(
    contract: ModelValidatorSubcontract,
) -> ModelMergeQueueParityRules:
    """The parity rule data of ``contract``; a missing row or parameter raises."""
    rows = _rows(contract)
    trigger = _row(rows, "trigger_events")
    expression = _row(rows, "condition_expression")
    report = _row(rows, "finding_report")
    return ModelMergeQueueParityRules(
        queue_event=rule_string(trigger, "queue_event"),
        pull_request_event=rule_string(trigger, "pull_request_event"),
        pull_request_events=rule_strings(trigger, "pull_request_events"),
        path_filter_keys=rule_strings(trigger, "path_filter_keys"),
        event_atom_pattern=rule_string(expression, "event_atom_pattern"),
        draft_atom_pattern=rule_string(expression, "draft_atom_pattern"),
        needs_output_pattern=rule_string(expression, "needs_output_pattern"),
        event_name_pattern=rule_string(expression, "event_name_pattern"),
        max_unknowns=rule_int(expression, "max_unknowns"),
        remediation=rule_string(report, "remediation"),
        finding_template=rule_string(report, "finding_template"),
        baselined_template=rule_string(report, "baselined_template"),
        stale_template=rule_string(report, "stale_template"),
        no_pull_request_trigger_message=rule_string(
            _row(rows, "no_pull_request_trigger"), "message_template"
        ),
        pull_request_path_filter_message=rule_string(
            _row(rows, "pull_request_path_filter"), "message_template"
        ),
        merge_queue_only_if_message=rule_string(
            _row(rows, "merge_queue_only_if"), "message_template"
        ),
        event_dependent_gate_message=rule_string(
            _row(rows, "event_dependent_gate"), "message_template"
        ),
    )


@cache
def load_parity_rules() -> ModelMergeQueueParityRules:
    """Load the parity rule data shipped with the package."""
    return parity_rules_from_contract(load_parity_contract())
