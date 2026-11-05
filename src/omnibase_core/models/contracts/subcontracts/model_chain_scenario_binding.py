# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Dependency a chain scenario binds into the handler under test (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chain_scenario_binding_role import (
    EnumChainScenarioBindingRole,
)
from omnibase_core.enums.enum_chain_scenario_binding_target import (
    EnumChainScenarioBindingTarget,
)
from omnibase_core.enums.enum_chain_scenario_fault_kind import (
    EnumChainScenarioFaultKind,
)


class ModelChainScenarioBinding(BaseModel):
    """One injected dependency: where it goes, its in-memory factory and its fault factories.

    Factories are ``module:callable`` paths. The in-memory factory is the default; a fault
    swaps in the factory declared for that fault kind through the same binding.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ..., min_length=1, description="Binding name; cases and faults refer to it."
    )
    target: EnumChainScenarioBindingTarget
    attribute: str = Field(
        ..., min_length=1, description="Constructor keyword or attribute name."
    )
    role: EnumChainScenarioBindingRole = EnumChainScenarioBindingRole.DEPENDENCY
    in_memory_factory: str = Field(..., pattern=r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
    fault_factories: dict[EnumChainScenarioFaultKind, str] = Field(default_factory=dict)


__all__ = ["ModelChainScenarioBinding"]
