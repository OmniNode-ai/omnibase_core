# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule values of the FSM single-source check, read from its validator contract (OMN-21513)."""

from __future__ import annotations

import ast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_fsm_single_source_rules import (
    ModelFsmSingleSourceRules,
)

__all__ = ["node_type_prefix_from_subcontract", "rules_from_subcontract"]


def _invalid(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def _parameter(rule: ModelValidatorRule | None, name: str) -> object:
    if rule is None:
        return None
    if rule.parameters is None or name not in rule.parameters:
        raise _invalid(f"Missing required parameter: {name}")
    return rule.parameters[name]


def _string_parameter(rule: ModelValidatorRule | None, name: str) -> str:
    value = _parameter(rule, name)
    if rule is None:
        return ""
    if not isinstance(value, str):
        raise _invalid(f"{name} must be a string")
    return value


def _strings_parameter(rule: ModelValidatorRule | None, name: str) -> tuple[str, ...]:
    value = _parameter(rule, name)
    if rule is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _invalid(f"{name} must be a list of strings")
    return tuple(value)


def _int_parameter(rule: ModelValidatorRule | None, name: str) -> int:
    value = _parameter(rule, name)
    if rule is None:
        return 0
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid(f"{name} must be an integer")
    return value


def _ast_parameter(
    rule: ModelValidatorRule | None, name: str
) -> tuple[type[ast.AST], ...]:
    nodes: list[type[ast.AST]] = []
    for entry in _strings_parameter(rule, name):
        node: object = getattr(ast, entry, None)
        if not isinstance(node, type) or not issubclass(node, ast.AST):
            raise _invalid(f"{name} contains an invalid AST node: {entry}")
        nodes.append(node)
    return tuple(nodes)


def rules_from_subcontract(
    contract: ModelValidatorSubcontract,
) -> ModelFsmSingleSourceRules:
    """Resolve rule parameters, rejecting missing or malformed configuration."""
    by_id = {rule.rule_id: rule for rule in contract.rules}
    machine = by_id.get("state_machine_missing")
    table = by_id.get("state_table")
    branch = by_id.get("state_branch_chain")
    executor = by_id.get("execute_transition_missing")
    return ModelFsmSingleSourceRules(
        severity_by_rule=tuple(
            (rule.rule_id, rule.severity) for rule in contract.rules if rule.enabled
        ),
        state_machine_key=_string_parameter(machine, "state_machine_key"),
        state_list_key=_string_parameter(machine, "state_list_key"),
        state_name_key=_string_parameter(machine, "state_name_key"),
        state_scalar_keys=_strings_parameter(machine, "state_scalar_keys"),
        state_list_keys=_strings_parameter(machine, "state_list_keys"),
        transition_list_key=_string_parameter(machine, "transition_list_key"),
        transition_state_keys=_strings_parameter(machine, "transition_state_keys"),
        collection_nodes=_ast_parameter(table, "collection_nodes"),
        enum_base_suffixes=_strings_parameter(table, "enum_base_suffixes"),
        min_table_states=_int_parameter(table, "min_table_states"),
        scope_nodes=_ast_parameter(branch, "scope_nodes"),
        compare_operators=_ast_parameter(branch, "compare_operators"),
        min_branches=_int_parameter(branch, "min_branches"),
        min_branch_states=_int_parameter(branch, "min_branch_states"),
        executor_name=_string_parameter(executor, "executor_name"),
    )


def node_type_prefix_from_subcontract(
    contract: ModelValidatorSubcontract,
) -> str | None:
    """The node_type prefix of the contracts the check applies to, or None without the rule."""
    rule = next(
        (r for r in contract.rules if r.rule_id == "state_machine_missing"), None
    )
    return None if rule is None else _string_parameter(rule, "node_type_prefix")
