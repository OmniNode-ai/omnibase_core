# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed fail-closed contract view for invariant analysis (OMN-21565)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_rule import (
    ModelInvariantAnalysisRule,
)

__all__ = ["ModelInvariantAnalysisRules"]

# Names and types are schema. All syntax and policy values belong to the contract.
_TEXT_KEYS = {
    "analysis_section_missing": ("heading_pattern", "section_end_pattern"),
    "scope_declaration_missing_or_unknown": ("scopes_pattern", "scope_split_pattern"),
    "invariant_unaddressed": (),
    "satisfied_by_task_absent": ("entry_pattern", "task_split_pattern"),
    "not_applicable_unreasoned": ("entry_pattern", "trim_pattern"),
    "invariant_unknown_or_retired": ("entry_pattern",),
    "registry_invalid": (
        "overlay_filename",
        "id_pattern",
        "active_status",
        "superseded_status",
        "lifecycle_entries_key",
        "lifecycle_path_key",
        "lifecycle_status_key",
    ),
    "authority_doc_coverage": (
        "marker_pattern",
        "coverage_start",
        "coverage_end",
        "id_pattern",
        "fence_pattern",
        "scope_split_pattern",
        "markdown_glob",
    ),
}
_LIST_KEYS = {
    "registry_invalid": ("required_fields", "required_ruled_fields", "valid_statuses"),
    "authority_doc_coverage": ("scan_exclusions",),
}
_INT_KEYS = {"authority_doc_coverage": ("header_scan_lines",)}
_GROUPS = {
    ("scope_declaration_missing_or_unknown", "scopes_pattern"): 1,
    ("satisfied_by_task_absent", "entry_pattern"): 2,
    ("not_applicable_unreasoned", "entry_pattern"): 2,
    ("invariant_unknown_or_retired", "entry_pattern"): 1,
    ("authority_doc_coverage", "marker_pattern"): 1,
}


def _error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelInvariantAnalysisRules(BaseModel):
    """Every required row, including disabled rows, validated before evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: dict[str, ModelInvariantAnalysisRule] = Field(
        description="Typed rows indexed by rule identifier"
    )

    def row(self, rule_id: str) -> ModelInvariantAnalysisRule:
        """Return a required rule."""
        return self.rows[rule_id]

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelInvariantAnalysisRules:
        """Reject missing or ill-typed parameters and malformed expressions."""
        by_id = {row.rule_id: row for row in contract.rules}
        if len(by_id) != len(contract.rules):
            raise _error("Duplicate rule identifiers")
        rows: dict[str, ModelInvariantAnalysisRule] = {}
        for rule_id, keys in _TEXT_KEYS.items():
            if rule_id not in by_id:
                raise _error(f"{rule_id}: required rule absent")
            row = by_id[rule_id]
            params = row.parameters or {}
            texts: dict[str, str] = {}
            for key in ("message", "remediation", *keys):
                value = params.get(key)
                if not isinstance(value, str) or not value:
                    raise _error(f"{rule_id}: {key} must be nonempty text")
                if key.endswith("_pattern"):
                    try:
                        expression = re.compile(value)
                    except re.error as exc:
                        raise _error(f"{rule_id}: invalid expression {key}") from exc
                    if expression.groups < _GROUPS.get((rule_id, key), 0):
                        raise _error(f"{rule_id}: {key} lacks capture groups")
                texts[key] = value
            lists: dict[str, tuple[str, ...]] = {}
            for key in _LIST_KEYS.get(rule_id, ()):
                value = params.get(key)
                if not isinstance(value, list) or not all(
                    isinstance(item, str) and item for item in value
                ):
                    raise _error(f"{rule_id}: {key} must be a text list")
                if rule_id == "registry_invalid" and not value:
                    raise _error(f"{rule_id}: {key} must not be empty")
                lists[key] = tuple(value)
            integers: dict[str, int] = {}
            for key in _INT_KEYS.get(rule_id, ()):
                value = params.get(key)
                if type(value) is not int or value < 1:
                    raise _error(f"{rule_id}: {key} must be a positive integer")
                integers[key] = value
            rows[rule_id] = ModelInvariantAnalysisRule(
                enabled=row.enabled,
                severity=row.severity,
                texts=texts,
                lists=lists,
                integers=integers,
            )
        return cls(rows=rows)
