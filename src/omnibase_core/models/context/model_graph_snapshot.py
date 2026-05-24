# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGraphSnapshot — lightweight architecture dependency graph snapshot (OMN-11928)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.context.model_context_provenance import ModelContextProvenance

__all__ = ["ModelGraphSnapshot"]


class ModelGraphSnapshot(BaseModel):
    """Lightweight snapshot of the architecture dependency graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_count: int = Field(ge=0, description="Number of nodes in the snapshot")
    edge_count: int = Field(ge=0, description="Number of edges in the snapshot")
    summary: str = Field(description="Natural language summary of key dependencies")
    provenance: ModelContextProvenance = Field(description="Source provenance")
