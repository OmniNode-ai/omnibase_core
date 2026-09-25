# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Totals over one contract walk (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkSummary(BaseModel):
    """Counts across every walked workflow in one report."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contracts_scanned: int = Field(description="contract.yaml files read")
    machine_contracts: int = Field(description="Contracts that declare a machine")
    walked_contracts: int = Field(
        description="Machine contracts loaded strictly and walked"
    )
    not_armed_contracts: int = Field(
        description="Machine contracts the walker could not load"
    )
    workflows: int = Field(description="Workflows walked")
    selected_paths: int = Field(description="Paths selected by the all-edges cover")
    golden_paths: int = Field(
        description="Selected paths ending in a non-error terminal"
    )
    error_paths: int = Field(
        description="Selected paths ending in a declared error state"
    )
    open_paths: int = Field(description="Selected paths that reach no terminal")
    error_edges: int = Field(
        description="Declared transitions into an error state that fire"
    )
    illegal_pairs: int = Field(
        description="(state, trigger) pairs a component must reject"
    )
    unreachable_states: int = Field(description="Declared states no walk reaches")
    dead_states: int = Field(
        description="Reached product states with no path to a terminal"
    )
    no_golden_exit_states: int = Field(
        description="Reached product states whose only reachable terminals are error states"
    )
    uncovered_transitions: int = Field(
        description="Declared transitions no reachable edge fires"
    )
    truncated_workflows: int = Field(
        description="Workflows whose product graph hit the state cap"
    )
