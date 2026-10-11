# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the imperative contract guard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_contract_source import (
    ModelGuardContractSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_module_source import (
    ModelGuardModuleSource,
)

__all__ = ["ModelImperativeContractGuardInput"]


class ModelImperativeContractGuardInput(BaseModel):
    """One repository's sources and allowlisted paths, with no I/O behind them."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository (package) name reported on every result.")
    nodes: list[ModelComplianceNodeSource] = Field(
        default_factory=list,
        description="node_* directories with a handlers/ directory, in scan order.",
    )
    allowlisted_paths: list[str] = Field(
        default_factory=list,
        description="Paths baselined by the repository's allowlist.",
    )
    scan_freestanding: bool = Field(
        default=False,
        description="Also audit every src/ module outside node handlers.",
    )
    modules: list[ModelGuardModuleSource] = Field(
        default_factory=list,
        description="Every src/**/*.py module (the import graph and the freestanding set).",
    )
    contracts: list[ModelGuardContractSource] = Field(
        default_factory=list,
        description="Every src/**/contract.yaml (live-entrypoint roots).",
    )
    pyproject_text: str | None = Field(
        default=None,
        description="Text of the repository's pyproject.toml, or None when absent.",
    )
