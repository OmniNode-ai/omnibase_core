# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved contract parameters for the FSM single-source checker."""

from __future__ import annotations

import ast

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums import EnumSeverity


class ModelFsmSingleSourceRules(BaseModel):
    """Immutable rule configuration with resolved Python AST node classes."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, arbitrary_types_allowed=True
    )

    severity_by_rule: tuple[tuple[str, EnumSeverity], ...]
    state_machine_key: str
    state_list_key: str
    state_name_key: str
    state_scalar_keys: tuple[str, ...]
    state_list_keys: tuple[str, ...]
    transition_list_key: str
    transition_state_keys: tuple[str, ...]
    collection_nodes: tuple[type[ast.AST], ...]
    enum_base_suffixes: tuple[str, ...]
    min_table_states: int
    scope_nodes: tuple[type[ast.AST], ...]
    compare_operators: tuple[type[ast.AST], ...]
    min_branches: int
    min_branch_states: int
    executor_name: str

    def severity_of(self, rule_id: str) -> EnumSeverity | None:
        """Return the configured severity for an enabled rule, if present."""
        return next(
            (severity for name, severity in self.severity_by_rule if name == rule_id),
            None,
        )
