# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextProvenance — source provenance for a context section (OMN-11928)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_knowledge_provider_kind import EnumKnowledgeProviderKind

__all__ = ["ModelContextProvenance"]


class ModelContextProvenance(BaseModel):
    """Source provenance for a single context section.

    The backend that produced an item is recorded in two parts (OMN-18372).
    ``provider_kind`` is the closed, vendor-neutral class of backend and is the
    only half a consumer may branch on. ``provider_name`` is the adapter's own
    identifier for the concrete instance it called, carried as data — it is the
    only field in this model where a product name may appear.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_kind: EnumKnowledgeProviderKind = Field(
        description="Generic class of backend that produced this item"
    )
    provider_name: str = Field(
        description=(
            "Adapter-supplied name of the concrete backend instance; the only "
            "field carrying a vendor identity, and it is data, not type"
        )
    )
    # string-id-ok: external system identifier, not an internal UUID
    source_id: str = Field(
        description="Stable identifier of this item within the provider"
    )
    source_hash: str = Field(description="Content hash for cache invalidation")
    retrieved_at: datetime = Field(
        description="UTC timestamp when this item was fetched"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Retrieval confidence in [0, 1]"
    )
