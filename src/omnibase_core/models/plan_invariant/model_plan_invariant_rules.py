# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the plan-invariant contract rules (OMN-21559)."""

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
    "task_without_falsifiable_criterion": (),
    "task_names_literal_value": (),
    "invariant_without_enforcing_task": (
        "invariants_heading_pattern",
        "section_end_pattern",
        "invariant_pattern",
        "enforces_pattern",
        "id_pattern",
    ),
}
_LIST_KEYS: dict[str, tuple[str, ...]] = {
    "task_names_literal_value": ("literal_kinds",),
}


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelPlanInvariantRules(BaseModel):
    """Validated rule rows and the compiled, extensible literal kinds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: dict[str, ModelTaskCriteriaRuleRow] = Field(
        description="Rule rows by rule id"
    )
    literal_kinds: tuple[tuple[str, re.Pattern[str]], ...] = Field(
        description="Literal kind names paired with their compiled expressions"
    )

    def row(self, rule_id: str) -> ModelTaskCriteriaRuleRow:
        """The row of a known rule."""
        return self.rows[rule_id]

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelPlanInvariantRules:
        """Require every rule and parameter, including those of disabled rows."""
        by_id = {rule.rule_id: rule for rule in contract.rules}
        rows: dict[str, ModelTaskCriteriaRuleRow] = {}
        kinds: list[tuple[str, re.Pattern[str]]] = []
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
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a list of strings"
                    )
                lists[name] = tuple(value)
                for item in value:
                    kind, separator, expression = item.partition("::")
                    if not separator or not kind or not expression:
                        raise _contract_error(
                            f"{rule_id}: parameter {name} requires <kind>::<regex> entries"
                        )
                    try:
                        kinds.append((kind, re.compile(expression)))
                    except re.error as exc:
                        raise _contract_error(
                            f"{rule_id}: parameter {name} has an invalid regular expression"
                        ) from exc
            rows[rule_id] = ModelTaskCriteriaRuleRow(
                enabled=rule.enabled,
                severity=rule.severity,
                message=texts.pop("message"),
                source_pattern=texts.pop("source_pattern"),
                texts=texts,
                lists=lists,
            )
        return cls(rows=rows, literal_kinds=tuple(kinds))
