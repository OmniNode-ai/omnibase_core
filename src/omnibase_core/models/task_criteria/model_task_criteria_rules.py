# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the task-criteria contract rules (OMN-21535)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.task_criteria.model_task_criteria_rule_row import (
    ModelTaskCriteriaRuleRow,
)

# The names each rule row must carry: schema, never values. A string name ending in
# ``_pattern`` is compiled when the contract loads.
_TEXT_KEYS: dict[str, tuple[str, ...]] = {
    "missing_configuration_criterion": (
        "task_heading_pattern",
        "criterion_pattern",
        "configuration_pattern",
    ),
    "missing_bindings_criterion": ("bindings_pattern",),
    "criterion_without_falsifier": (
        "falsifier_pattern",
        "action_pattern",
        "observable_pattern",
    ),
    "missing_two_overlay_falsifier": (
        "applies_pattern",
        "in_memory_pattern",
        "broker_pattern",
        "no_code_change_pattern",
    ),
    "replay_only_bindings_falsifier": ("replay_only_pattern", "live_evidence_pattern"),
    "missing_zero_literal_falsifier": ("applies_pattern", "zero_pattern"),
    "missing_container_resolution_criterion": ("applies_pattern", "resolution_pattern"),
    "brief_missing_rule_block": ("block_start", "block_end", "escaped_newline"),
    "rule_block_incomplete": ("block_start", "block_end"),
    "task_in_frozen_repository": (
        "files_pattern",
        "repository_pattern",
        "fix_pattern",
        "release_pattern",
    ),
}
_LIST_KEYS: dict[str, tuple[str, ...]] = {
    "missing_zero_literal_falsifier": ("validator_names",),
    "brief_missing_rule_block": ("accepted_digests",),
    "rule_block_incomplete": ("required_items",),
    "task_in_frozen_repository": ("frozen_states", "fix_permitted_states"),
}


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelTaskCriteriaRules(BaseModel):
    """Every rule row of the contract, validated when the contract is read."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: dict[str, ModelTaskCriteriaRuleRow] = Field(
        description="Rule rows by rule id"
    )

    def row(self, rule_id: str) -> ModelTaskCriteriaRuleRow:
        """The row of a known rule."""
        return self.rows[rule_id]

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelTaskCriteriaRules:
        """Require every rule and every parameter, including those of disabled rules."""
        by_id = {rule.rule_id: rule for rule in contract.rules}
        rows: dict[str, ModelTaskCriteriaRuleRow] = {}
        for rule_id, text_keys in _TEXT_KEYS.items():
            if rule_id not in by_id:
                raise _contract_error(f"{rule_id}: required rule is absent")
            rule = by_id[rule_id]
            params = rule.parameters or {}
            texts: dict[str, str] = {}
            for name in ("message", "source_pattern", *text_keys):
                value = params.get(name)
                if not isinstance(value, str):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a string"
                    )
                if name.endswith("_pattern"):
                    try:
                        re.compile(value)
                    except re.error as exc:
                        raise _contract_error(
                            f"{rule_id}: parameter {name} is not a regular expression"
                        ) from exc
                texts[name] = value
            lists: dict[str, tuple[str, ...]] = {}
            for name in _LIST_KEYS.get(rule_id, ()):
                value = params.get(name)
                if not isinstance(value, list):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a list of strings"
                    )
                lists[name] = tuple(value)
            rows[rule_id] = ModelTaskCriteriaRuleRow(
                enabled=rule.enabled,
                severity=rule.severity,
                message=texts.pop("message"),
                source_pattern=texts.pop("source_pattern"),
                texts=texts,
                lists=lists,
            )
        return cls(rows=rows)
