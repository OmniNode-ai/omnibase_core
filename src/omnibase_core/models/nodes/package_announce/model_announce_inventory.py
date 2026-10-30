# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The previous inventory of one announcer, kept for withdrawal after a restart (OMN-21589)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.package_announce.model_announce_inventory_entry import (
    ModelAnnounceInventoryEntry,
)


class ModelAnnounceInventory(BaseModel):
    """What an announcer published at its last boot.

    Attributes:
        contracts: Contract name to the identity last published for it.
        generations: Distribution name to the last generation the announcer used.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contracts: dict[str, ModelAnnounceInventoryEntry] = Field(default_factory=dict)
    generations: dict[str, int] = Field(default_factory=dict)
