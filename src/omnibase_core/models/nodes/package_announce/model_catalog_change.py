# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A change the catalog made, delivered to ``watch()`` (OMN-21589)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_catalog_entry_state import EnumCatalogEntryState
from omnibase_core.models.nodes.package_announce.model_catalog_entry import (
    ModelCatalogEntry,
)


class ModelCatalogChange(BaseModel):
    """One entry's move from ``previous_state`` (``None`` for a new name) to ``entry``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    previous_state: EnumCatalogEntryState | None
    entry: ModelCatalogEntry
