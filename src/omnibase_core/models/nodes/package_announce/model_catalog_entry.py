# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One contract name in the node catalog (OMN-21589)."""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from omnibase_core.enums.enum_announced_node_kind import EnumAnnouncedNodeKind
from omnibase_core.enums.enum_catalog_entry_state import EnumCatalogEntryState
from omnibase_core.models.events.contract_registration.model_announced_package import (
    ModelAnnouncedPackage,
)


class ModelCatalogEntry(BaseModel):
    """What the catalog holds for one contract name.

    Identity is the content hash together with the package reference. A withdrawn
    entry keeps the generation of the newest withdrawal, so a delayed older
    announcement cannot resurrect it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    state: EnumCatalogEntryState
    content_hash: str
    package: ModelAnnouncedPackage
    node_kind: EnumAnnouncedNodeKind
    declared_topics: tuple[str, ...]
    handler_dependencies: tuple[str, ...]
    announcer_id: UUID
    generation: int
    contract_path: Path | None = None
    refusal_reason: EnumAnnounceRefusalReason | None = None
