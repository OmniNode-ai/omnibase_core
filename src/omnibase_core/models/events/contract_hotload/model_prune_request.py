# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request to prune topics that no installed contract declares (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_hotload.model_prune_candidate import (
    ModelPruneCandidate,
)

__all__ = ["ModelPruneRequest"]


class ModelPruneRequest(BaseModel):
    """A caller proposes topics for retirement and states what it saw.

    Attributes:
        entity_id: The prune id.
        candidates: The topics proposed, each with its end offsets and groups.
        inventory_digest: Digest of the caller's topic inventory, so the registry
            can tell a request made from a stale inventory.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    candidates: tuple[ModelPruneCandidate, ...]
    inventory_digest: str = Field(min_length=1)
