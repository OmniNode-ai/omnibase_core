# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed rule data of the bare-feature-flag check (OMN-20074, OMN-21518).

The patterns, approved names and segments and the message templates are the
``parameters`` of the rule rows of ``contracts/no_bare_feature_flags.validation.yaml``;
this module reads them into the typed rules the pure handler takes. A missing or
mistyped parameter raises, so a broken contract fails to load instead of passing
every file.
"""

from __future__ import annotations

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_rules import (
    ModelBareFeatureFlagRules,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_READ = "bare_feature_flag_read"
RULE_BARE_EXEMPTION = "exemption_without_reason"
RULE_EXEMPTION = "exemption_listed"
RULE_SUMMARY = "hook_summary"


def load_rules(contract: ModelValidatorSubcontract) -> ModelBareFeatureFlagRules:
    """The rule rows of ``contract`` as the typed rules of the handler."""
    rows = {rule.rule_id: rule for rule in contract.rules}
    read, bare, exempt = (
        rows[RULE_READ],
        rows[RULE_BARE_EXEMPTION],
        rows[RULE_EXEMPTION],
    )
    return ModelBareFeatureFlagRules(
        python_pattern=rule_string(read, "python_pattern"),
        ts_pattern=rule_string(read, "ts_pattern"),
        comment_prefixes=rule_strings(read, "comment_prefixes"),
        approved_basenames=rule_strings(read, "approved_basenames"),
        approved_path_segments=rule_strings(read, "approved_path_segments"),
        violation_template=rule_string(read, "message_template"),
        exempt_with_reason_pattern=rule_string(bare, "exempt_with_reason_pattern"),
        exempt_bare_pattern=rule_string(bare, "exempt_bare_pattern"),
        bare_exemption_template=rule_string(bare, "message_template"),
        exemption_template=rule_string(exempt, "message_template"),
    )


__all__ = [
    "RULE_BARE_EXEMPTION",
    "RULE_EXEMPTION",
    "RULE_READ",
    "RULE_SUMMARY",
    "load_rules",
]
