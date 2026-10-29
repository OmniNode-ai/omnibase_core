# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)


class ModelFirstPartyRefInput(BaseModel):
    """Supplied source snapshots and independently gathered tag inventories."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    files: tuple[ModelSourceFile, ...]
    dev_tags: tuple[ModelFirstPartyTagInventoryResult, ...] = ()
