# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reads of a rule row's ``parameters`` for the generic-format checkers (OMN-21503).

Every pattern, name list and remediation text of a checker is a ``parameters``
entry of its ``.validation.yaml`` rule row. A missing or mistyped entry is an
invalid contract and raises, so a broken contract fails to load instead of
passing every file.
"""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)


def rule_strings(rule: ModelValidatorRule, key: str) -> tuple[str, ...]:
    """A list-of-strings parameter of ``rule``; raises when absent or mistyped."""
    value = (rule.parameters or {}).get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r} needs a list of strings under parameters.{key}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return tuple(value)


def rule_string(rule: ModelValidatorRule, key: str) -> str:
    """A string parameter of ``rule``; raises when absent or mistyped."""
    value = (rule.parameters or {}).get(key)
    if not isinstance(value, str) or not value:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r} needs a non-empty string under parameters.{key}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return value


def rule_int(rule: ModelValidatorRule, key: str) -> int:
    """An integer parameter of ``rule``; raises when absent or mistyped."""
    value = (rule.parameters or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r} needs an integer under parameters.{key}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return value


__all__ = ["rule_int", "rule_string", "rule_strings"]
