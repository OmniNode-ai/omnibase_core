# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the merge-receipt contract rules (OMN-21926)."""

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
    "runtime_paths": (),
    "receipt_sources": (),
    "slot_time": ("surface_pattern", "min_pairs"),
    "receipt_missing": (),
    "receipt_stale_head": (),
    "lab_line_not_receipt": ("lab_line_pattern",),
}
_LIST_KEYS: dict[str, tuple[str, ...]] = {
    "runtime_paths": ("runtime_path_patterns", "exempt_path_patterns"),
    "receipt_sources": ("machine_sources", "watcher_check_names"),
}
_PATTERN_LISTS = frozenset({"runtime_path_patterns", "exempt_path_patterns"})
_NONEMPTY_LISTS = frozenset({"runtime_path_patterns", "machine_sources"})


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def _compile(rule_id: str, name: str, expression: str) -> re.Pattern[str]:
    try:
        return re.compile(expression)
    except re.error as exc:
        raise _contract_error(
            f"{rule_id}: parameter {name} has an invalid regular expression"
        ) from exc


class ModelMergeReceiptRules(BaseModel):
    """Validated rule rows and the compiled path patterns."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: dict[str, ModelTaskCriteriaRuleRow] = Field(
        description="Rule rows by rule id"
    )
    runtime: tuple[re.Pattern[str], ...] = Field(
        description="Compiled paths that make a pull request runtime-affecting"
    )
    exempt: tuple[re.Pattern[str], ...] = Field(
        description="Compiled paths that never make a pull request runtime-affecting"
    )

    def row(self, rule_id: str) -> ModelTaskCriteriaRuleRow:
        """The row of a known rule."""
        return self.rows[rule_id]

    def is_runtime_path(self, path: str) -> bool:
        """Whether one changed path runs: not exempt, and a runtime pattern selects it."""
        if any(p.search(path) for p in self.exempt):
            return False
        return any(p.search(path) for p in self.runtime)

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelMergeReceiptRules:
        """Require every rule and parameter, including those of disabled rows."""
        by_id = {rule.rule_id: rule for rule in contract.rules}
        rows: dict[str, ModelTaskCriteriaRuleRow] = {}
        runtime: tuple[re.Pattern[str], ...] = ()
        exempt: tuple[re.Pattern[str], ...] = ()
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
                    _compile(rule_id, name, value)
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
                if name in _NONEMPTY_LISTS and (
                    not value or any(item.strip() == "" for item in value)
                ):
                    raise _contract_error(
                        f"{rule_id}: parameter {name} must name at least one non-blank entry"
                    )
                lists[name] = tuple(value)
                if name in _PATTERN_LISTS:
                    compiled = tuple(_compile(rule_id, name, e) for e in value)
                    if name == "runtime_path_patterns":
                        runtime = compiled
                    else:
                        exempt = compiled
            rows[rule_id] = ModelTaskCriteriaRuleRow(
                enabled=rule.enabled,
                severity=rule.severity,
                message=texts.pop("message"),
                source_pattern=texts.pop("source_pattern"),
                texts=texts,
                lists=lists,
            )
        return cls(rows=rows, runtime=runtime, exempt=exempt)
