# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolve the handler a validator rule is bound to through its contract (OMN-21494).

A validator is the generic compute node: its rules are data, and a rule that cannot be
data names a handler in the rule row (``handler: <dotted.module>:<callable>``). This module
turns that reference into the callable, and refuses a reference that does not resolve, so a
rule bound to a handler that is not there fails to load instead of passing every file.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)


def resolve_rule_handler(rule: ModelValidatorRule) -> Callable[..., object] | None:
    """The callable ``rule.handler`` names, or ``None`` for a rule judged by its parameters alone."""
    if rule.handler is None:
        return None
    module_path, _, name = rule.handler.partition(":")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r} binds handler {rule.handler!r}: module does not import: {exc}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        ) from exc
    target = getattr(module, name, None)
    if not callable(target):
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r} binds handler {rule.handler!r}: {module_path} has no callable {name!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return target
