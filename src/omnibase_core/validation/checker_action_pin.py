# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure rule-data reader of the action-pin check (OMN-17427, OMN-21518).

The rule rows of ``contracts/action_pin.validation.yaml`` in, the typed
``ModelActionPinRules`` out. A missing or mistyped parameter raises, so a broken
contract fails to load instead of passing every workflow.
"""

from __future__ import annotations

from collections.abc import Mapping

from omnibase_core.models.action_pins.model_action_pin_rules import (
    ModelActionPinRules,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_EXTRACTION = "uses_extraction"
RULE_THIRD_PARTY = "third_party_not_sha"
RULE_FIRST_PARTY = "first_party_not_tag"
RULE_MAIN = "first_party_main_allowance"
RULE_EXCEPTION_USED = "known_exception_used"
RULE_EXCEPTION_STALE = "known_exception_stale"


def action_pin_rules(rules: Mapping[str, ModelValidatorRule]) -> ModelActionPinRules:
    """The typed rule data of the action-pin contract's rows."""
    extraction = rules[RULE_EXTRACTION]
    third = rules[RULE_THIRD_PARTY]
    first = rules[RULE_FIRST_PARTY]
    return ModelActionPinRules(
        report_validator_name=rule_string(extraction, "report_validator_name"),
        workflow_dir=rule_string(extraction, "workflow_dir"),
        workflow_suffixes=rule_strings(extraction, "workflow_suffixes"),
        local_prefixes=rule_strings(extraction, "local_prefixes"),
        block_uses_pattern=rule_string(extraction, "block_uses_pattern"),
        flow_uses_pattern=rule_string(extraction, "flow_uses_pattern"),
        full_sha_pattern=rule_string(third, "full_sha_pattern"),
        main_ref=rule_string(first, "main_ref"),
        third_party_message=rule_string(third, "message_template"),
        third_party_remediation=rule_string(third, "remediation"),
        first_party_tag_message=rule_string(first, "message_template"),
        first_party_remediation=rule_string(first, "remediation"),
        first_party_main_message=rule_string(rules[RULE_MAIN], "message_template"),
        known_exception_message=rule_string(
            rules[RULE_EXCEPTION_USED], "message_template"
        ),
        stale_exception_message=rule_string(
            rules[RULE_EXCEPTION_STALE], "message_template"
        ),
    )


__all__ = ["action_pin_rules"]
