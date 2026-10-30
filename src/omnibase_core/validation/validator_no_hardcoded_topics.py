# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNoHardcodedTopics -- the contract entry of the no-hardcoded-topics rules (OMN-21518).

The rule data is the rule rows of ``contracts/no_hardcoded_topics.validation.yaml``;
``load_rules`` reads them into the typed rules the pure COMPUTE node
``node_no_hardcoded_topics_check_compute`` judges with. The rules read the source
texts of the files a hook names, so this entry has no per-file rule of its own.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_rules import (
    ModelNoHardcodedTopicsRules,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)
from omnibase_core.validation.validator_base import ValidatorBase

RULE_TOPIC_LITERAL = "topic_literal"
RULE_EXEMPT_PATH = "exempt_path"
RULE_SKIP_LINE = "skip_line"


def load_rules(contract: ModelValidatorSubcontract) -> ModelNoHardcodedTopicsRules:
    """Read the typed rules from the contract's rule rows.

    Raises:
        ModelOnexError: a row is missing or disabled, or a parameter is absent or
            mistyped, so a broken contract fails to load instead of passing every file.
    """
    rows = {rule.rule_id: rule for rule in contract.rules}
    for rule_id in (RULE_TOPIC_LITERAL, RULE_EXEMPT_PATH, RULE_SKIP_LINE):
        row = rows.get(rule_id)
        if row is None or not row.enabled:
            raise ModelOnexError(
                message=f"no_hardcoded_topics contract needs an enabled rule row {rule_id!r}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
    literal, exempt, skip = (
        rows[RULE_TOPIC_LITERAL],
        rows[RULE_EXEMPT_PATH],
        rows[RULE_SKIP_LINE],
    )
    return ModelNoHardcodedTopicsRules(
        validator_name=rule_string(literal, "validator_name"),
        topic_literal_pattern=rule_string(literal, "topic_literal_pattern"),
        message=rule_string(literal, "message"),
        remediation=rule_string(literal, "remediation"),
        approved_basenames=frozenset(rule_strings(exempt, "approved_basenames")),
        test_dir_marker=rule_string(exempt, "test_dir_marker"),
        test_name_prefix=rule_string(exempt, "test_name_prefix"),
        test_name_suffixes=rule_strings(exempt, "test_name_suffixes"),
        wire_schema_dir=rule_string(exempt, "wire_schema_dir"),
        wire_schema_name_pattern=rule_string(exempt, "wire_schema_name_pattern"),
        wire_schema_min_parts=rule_int(exempt, "wire_schema_min_parts"),
        comment_prefixes=rule_strings(skip, "comment_prefixes"),
        block_comment_open=rule_string(skip, "block_comment_open"),
        block_comment_close=rule_string(skip, "block_comment_close"),
        docstring_delimiters=rule_strings(skip, "docstring_delimiters"),
    )


class ValidatorNoHardcodedTopics(ValidatorBase):
    """Loads the no-hardcoded-topics contract; the COMPUTE node judges with it."""

    validator_id: ClassVar[str] = "no_hardcoded_topics"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """No per-file rule exists: the node judges supplied source texts."""
        return ()


__all__ = [
    "RULE_EXEMPT_PATH",
    "RULE_SKIP_LINE",
    "RULE_TOPIC_LITERAL",
    "ValidatorNoHardcodedTopics",
    "load_rules",
]
