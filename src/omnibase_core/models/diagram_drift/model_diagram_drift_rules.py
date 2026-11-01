# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of the diagram-drift contract rules (OMN-21510)."""

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
    "diagram_differs": (
        "no_line_text",
        "indent",
        "state_header",
        "graph_header",
        "initial_line",
        "transition_line",
        "priority_suffix",
        "conditions_suffix",
        "condition_join",
        "terminal_line",
        "compute_node_type",
        "compute_node_line",
        "node_line",
        "edge_line",
        "collapsed_edge_line",
        "quote",
        "quote_entity",
    ),
    "diagram_without_fragment": (),
    "fragment_without_diagram": (),
    "fragment_refused": ("mismatch_message",),
    "duplicate_fragment": (),
    "missing_contract_line": (),
    "malformed_marker": (
        "diagram_marker_pattern",
        "fragment_marker_pattern",
        "fence",
        "yaml_language",
        "mermaid_language",
        "missing_yaml_message",
        "missing_mermaid_message",
    ),
    "view_not_supported": (),
}
# Capture groups a marker pattern must expose: node, block and, for a diagram, the collapsed word.
_MIN_GROUPS: dict[str, int] = {
    "diagram_marker_pattern": 3,
    "fragment_marker_pattern": 2,
}


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelDiagramDriftRules(BaseModel):
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
    ) -> ModelDiagramDriftRules:
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
                if not isinstance(value, str):
                    raise _contract_error(
                        f"{rule_id}: required parameter {name} must be a string"
                    )
                if name.endswith("_pattern"):
                    try:
                        compiled = re.compile(value)
                    except re.error as exc:
                        raise _contract_error(
                            f"{rule_id}: parameter {name} is not a regular expression"
                        ) from exc
                    if compiled.groups < _MIN_GROUPS.get(name, 0):
                        raise _contract_error(
                            f"{rule_id}: parameter {name} needs {_MIN_GROUPS[name]} capture groups"
                        )
                texts[name] = value
            rows[rule_id] = ModelTaskCriteriaRuleRow(
                enabled=rule.enabled,
                severity=rule.severity,
                message=texts.pop("message"),
                source_pattern=texts.pop("source_pattern"),
                texts=texts,
            )
        return cls(rows=rows)
