# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``validator_shape``: the canonical shape of a validator (OMN-21494).

A validator is the generic compute node in omnibase_core: pure, so the same input gives
the same findings. Its rules are overlay data; a rule that cannot be data is a handler
bound through the contract. Reading inputs, emitting bus traces and failing a check are
separate effect nodes around it. Facts in (one node contract with its judged I/O),
``ModelValidationIssue`` out: no file read, no clock, no environment. Every tag, key and
required value is a ``parameters`` entry of the matching rule row in
``contracts/validator_shape.validation.yaml``; this module holds none.

Rules: validator_node_scope, validator_node_archetype, validator_node_impure,
validator_handler_unbound, validator_compute_step_io.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_validator_shape_node_fact import (
    ModelValidatorShapeNodeFact,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
    rule_strings,
)

RULE_SCOPE = "validator_node_scope"
RULE_ARCHETYPE = "validator_node_archetype"
RULE_IMPURE = "validator_node_impure"
RULE_UNBOUND = "validator_handler_unbound"
RULE_IO = "validator_compute_step_io"


def _issue(rule: ModelValidatorRule, path: Path, message: str) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=message,
        code=rule.rule_id,
        file_path=path,
        rule_name=rule.rule_id,
    )


def _active(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> bool:
    return rule_id in rules and rules[rule_id].enabled


def check_node(
    path: Path,
    node: ModelValidatorShapeNodeFact,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """The issues of a node tagged as a validator; nothing for any other node."""
    if not _active(rules, RULE_SCOPE):
        return ()
    if not set(node.tags) & set(rule_strings(rules[RULE_SCOPE], "validator_tags")):
        return ()
    issues: list[ModelValidationIssue] = []
    name = node.directory_name
    if _active(rules, RULE_ARCHETYPE):
        row = rules[RULE_ARCHETYPE]
        required = rule_string(row, "required_node_type")
        if node.node_type.lower() != required.lower():
            issues.append(
                _issue(
                    row,
                    path,
                    f"validator {name!r} declares node_type {node.node_type!r}, not {required!r}: {row.description}",
                )
            )
    if _active(rules, RULE_IMPURE):
        row = rules[RULE_IMPURE]
        required = rule_string(row, "required_purity")
        if node.purity.lower() != required.lower():
            issues.append(
                _issue(
                    row,
                    path,
                    f"validator {name!r} declares purity {node.purity!r}, not {required!r}: {row.description}",
                )
            )
    if _active(rules, RULE_UNBOUND) and not node.handler_bindings:
        row = rules[RULE_UNBOUND]
        issues.append(
            _issue(row, path, f"validator {name!r} binds no handler: {row.description}")
        )
    if _active(rules, RULE_IO):
        row = rules[RULE_IO]
        issues.extend(
            _issue(
                row,
                path,
                f"validator {name!r} does I/O in its compute step ({detail}): {row.description}",
            )
            for detail in node.compute_step_io
        )
    return tuple(issues)


__all__ = [
    "RULE_ARCHETYPE",
    "RULE_IMPURE",
    "RULE_IO",
    "RULE_SCOPE",
    "RULE_UNBOUND",
    "check_node",
]
