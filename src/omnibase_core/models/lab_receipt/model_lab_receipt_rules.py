# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the lab-receipt contract rules (OMN-21823)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_lab_receipt_phase import EnumLabReceiptPhase
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_file_class import (
    ModelLabReceiptFileClass,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_record import (
    ModelLabReceiptRecord,
)
from omnibase_core.models.task_criteria.model_task_criteria_rule_row import (
    ModelTaskCriteriaRuleRow,
)

# Parameter names are schema; their values belong only to the contract.
_PHASES = "phases"
_TEXT_KEYS: dict[str, tuple[str, ...]] = {
    "receipt_required": ("unclassified_class",),
    "receipt_criterion_missing": ("criterion_pattern",),
    "receipt_head_mismatch": (),
    "receipt_field_missing": (),
    "receipt_installer_undeclared": (),
    "receipt_revision_not_head": ("revision_pattern",),
    "receipt_observation_unproven": ("length_pattern",),
    "receipt_not_on_lab": (),
    "lab_read_unavailable": (),
}
_LIST_KEYS: dict[str, tuple[str, ...]] = {
    "receipt_required": (
        "counted_statuses",
        "prod_classes",
        "operative_classes",
        "exempt_classes",
        "runtime_classes",
    ),
    "receipt_field_missing": ("required_fields",),
    "receipt_installer_undeclared": ("installers",),
    "receipt_observation_unproven": ("observed_words", "refused_patterns"),
}
_REGEX_LISTS = frozenset({"refused_patterns"})
_CLASS_LISTS = (
    "prod_classes",
    "operative_classes",
    "exempt_classes",
    "runtime_classes",
)


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


def _file_class(rule_id: str, name: str, entry: str) -> ModelLabReceiptFileClass:
    label, first, rest = entry.partition("::")
    repository, second, path = rest.partition("::")
    if not (label and first and repository and second and path):
        raise _contract_error(
            f"{rule_id}: parameter {name} requires <class>::<repository>::<path> entries"
        )
    return ModelLabReceiptFileClass(
        name=label,
        repository=_compile(rule_id, name, repository),
        path=_compile(rule_id, name, path),
    )


class ModelLabReceiptRules(BaseModel):
    """Validated rule rows and the compiled file classes, by contract list name."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: dict[str, ModelTaskCriteriaRuleRow] = Field(
        description="Rule rows by rule id"
    )
    classes: dict[str, tuple[ModelLabReceiptFileClass, ...]] = Field(
        description="Compiled file classes by list name"
    )
    refused: tuple[re.Pattern[str], ...] = Field(
        description="Compiled refused observation shapes"
    )
    observed: tuple[re.Pattern[str], ...] = Field(
        description="Compiled whole-word patterns of the words that show a run"
    )

    def row(self, rule_id: str) -> ModelTaskCriteriaRuleRow:
        """The row of a known rule."""
        return self.rows[rule_id]

    def runs_in(self, rule_id: str, phase: EnumLabReceiptPhase) -> bool:
        """Whether the row is enabled and applies in a phase."""
        row = self.rows[rule_id]
        return row.enabled and phase.value in row.lists[_PHASES]

    @classmethod
    def from_contract(cls, contract: ModelValidatorSubcontract) -> ModelLabReceiptRules:
        """Require every rule and parameter, including those of disabled rows."""
        by_id = {rule.rule_id: rule for rule in contract.rules}
        rows: dict[str, ModelTaskCriteriaRuleRow] = {}
        classes: dict[str, tuple[ModelLabReceiptFileClass, ...]] = {}
        refused: tuple[re.Pattern[str], ...] = ()
        observed: tuple[re.Pattern[str], ...] = ()
        record_fields = frozenset(ModelLabReceiptRecord.model_fields)
        phases = frozenset(phase.value for phase in EnumLabReceiptPhase)
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
            for name in (_PHASES, *_LIST_KEYS.get(rule_id, ())):
                value = params.get(name)
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a list of strings"
                    )
                lists[name] = tuple(value)
                if name == _PHASES and not set(value) <= phases:
                    raise _contract_error(
                        f"{rule_id}: parameter {name} names an unknown phase"
                    )
                if name == "required_fields" and not set(value) <= record_fields:
                    raise _contract_error(
                        f"{rule_id}: parameter {name} names a field a receipt does not have"
                    )
                if name in _CLASS_LISTS:
                    classes[name] = tuple(_file_class(rule_id, name, e) for e in value)
                if name in _REGEX_LISTS:
                    refused = tuple(_compile(rule_id, name, e) for e in value)
                if name == "observed_words":
                    observed = tuple(
                        _compile(rule_id, name, rf"(?i)(?<!\w){re.escape(e)}(?!\w)")
                        for e in value
                    )
            rows[rule_id] = ModelTaskCriteriaRuleRow(
                enabled=rule.enabled,
                severity=rule.severity,
                message=texts.pop("message"),
                source_pattern=texts.pop("source_pattern"),
                texts=texts,
                lists=lists,
            )
        return cls(rows=rows, classes=classes, refused=refused, observed=observed)
