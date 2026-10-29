# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The diagram drift predicate's rule table, read from its contract."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)

_ISSUE_KINDS = frozenset(
    {
        "diagram_differs",
        "diagram_without_fragment",
        "fragment_without_diagram",
        "fragment_refused",
        "duplicate_fragment",
        "missing_contract_line",
        "malformed_marker",
        "view_not_supported",
    }
)


# The capture groups each marker pattern must have: node, block name and, for a diagram, the view keyword.
_MARKER_GROUPS = {"diagram_marker_pattern": 3, "fragment_marker_pattern": 2}


class ModelDiagramDriftRules(BaseModel):
    """Immutable syntax, view support, and enabled issue kinds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    diagram_marker_pattern: str
    fragment_marker_pattern: str
    fence: str
    fragment_language: str
    diagram_language: str
    full_view: str
    collapsed_view: str
    full_view_only_kinds: tuple[str, ...]
    enabled_kinds: frozenset[str]

    @field_validator("diagram_marker_pattern", "fragment_marker_pattern")
    @classmethod
    def _marker_pattern_compiles_with_its_groups(
        cls, pattern: str, info: ValidationInfo
    ) -> str:
        """A marker pattern compiles and captures the groups the checker reads."""
        field = str(info.field_name)
        groups = _MARKER_GROUPS[field]
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"{field} is not a valid pattern: {exc}") from exc
        if compiled.groups != groups:
            raise ValueError(f"{field} must capture {groups} groups")
        return pattern

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelDiagramDriftRules:
        """Read the table rules and the enabled issue kinds from the contract.

        A table rule that is missing or disabled, or a parameter that is absent or of the wrong
        type, fails the model's validation naming the field it feeds.
        """
        rules = {rule.rule_id: rule for rule in contract.rules if rule.enabled}

        def parameter(rule_id: str, name: str) -> RuleParameterValue | None:
            rule = rules.get(rule_id)
            if rule is None or rule.parameters is None:
                return None
            return rule.parameters.get(name)

        return cls.model_validate(
            {
                "diagram_marker_pattern": parameter("diagram_marker", "pattern"),
                "fragment_marker_pattern": parameter("fragment_marker", "pattern"),
                "fence": parameter("block_syntax", "fence"),
                "fragment_language": parameter("block_syntax", "fragment_language"),
                "diagram_language": parameter("block_syntax", "diagram_language"),
                "full_view": parameter("view_support", "full_view"),
                "collapsed_view": parameter("view_support", "collapsed_view"),
                "full_view_only_kinds": parameter(
                    "view_support", "full_view_only_kinds"
                ),
                "enabled_kinds": frozenset(rules) & _ISSUE_KINDS,
            }
        )
