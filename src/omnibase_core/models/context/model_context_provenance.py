# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextProvenance — source provenance for a context section (OMN-11928)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelContextProvenance"]


class ModelContextProvenance(BaseModel):
    """Source provenance for a single context section."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(
        description="Backend that produced this item (e.g. repowise, linear)"
    )
    source_id: str = (
        Field(  # string-id-ok: external system identifier, not an internal UUID
            description="Stable identifier within the source system"
        )
    )
    source_hash: str = Field(description="Content hash for cache invalidation")
    retrieved_at: datetime = Field(
        description="UTC timestamp when this item was fetched"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Retrieval confidence in [0, 1]"
    )
