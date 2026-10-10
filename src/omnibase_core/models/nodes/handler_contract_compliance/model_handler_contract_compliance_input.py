# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the handler-contract compliance check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)

__all__ = ["ModelHandlerContractComplianceInput"]


class ModelHandlerContractComplianceInput(BaseModel):
    """Explicit node sources and allowlisted handler paths, with no I/O behind them."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name reported on every result.")
    nodes: list[ModelComplianceNodeSource] = Field(default_factory=list)
    allowlisted_paths: list[str] = Field(
        default_factory=list,
        description="Handler paths (relative to the directory above the package) that are allowlisted.",
    )
