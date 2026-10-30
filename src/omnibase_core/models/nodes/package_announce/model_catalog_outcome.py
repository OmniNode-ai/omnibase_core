# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What the catalog did with one announcement (OMN-21589)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from omnibase_core.enums.enum_catalog_entry_state import EnumCatalogEntryState


class ModelCatalogOutcome(BaseModel):
    """Result of applying one announcement.

    ``state`` is the entry state after the announcement, or ``None`` when the
    catalog changed nothing (a stale generation, or a refused withdrawal).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    generation: int
    accepted: bool
    state: EnumCatalogEntryState | None = None
    refusal_reason: EnumAnnounceRefusalReason | None = None
