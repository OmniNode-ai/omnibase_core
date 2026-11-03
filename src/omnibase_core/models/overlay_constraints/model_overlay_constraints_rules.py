# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the overlay-constraints contract rules (OMN-22185)."""

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

# Parameter names are schema; their values belong only to the contract.
_TEXT_KEYS: dict[str, tuple[str, ...]] = {
    "relation_violated": (),
    "key_absent": (),
    "value_not_numeric": (),
    "relation_malformed": ("identifier_pattern", "number_pattern", "sum_separator"),
}
_LIST_KEYS: dict[str, tuple[str, ...]] = {
    "relation_violated": (),
    "key_absent": (),
    "value_not_numeric": (),
    "relation_malformed": ("operators",),
}


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelOverlayConstraintsRules(BaseModel):
    """Validated rule rows by rule id."""

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
    ) -> ModelOverlayConstraintsRules:
        """Require every rule and parameter, including those of disabled rows."""
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
                if not isinstance(value, str) or not value:
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a non-empty string"
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
            for name in _LIST_KEYS[rule_id]:
                value = params.get(name)
                if (
                    not isinstance(value, list)
                    or not value
                    or not all(isinstance(item, str) and item for item in value)
                ):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a non-empty list of strings"
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
