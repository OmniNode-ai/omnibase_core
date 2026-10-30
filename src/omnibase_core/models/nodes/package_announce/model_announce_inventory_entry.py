# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One contract in an announcer's persisted inventory (OMN-21589)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_announced_node_kind import EnumAnnouncedNodeKind
from omnibase_core.models.events.contract_registration.model_announced_package import (
    ModelAnnouncedPackage,
)


class ModelAnnounceInventoryEntry(BaseModel):
    """The identity an announcer last published for one contract name.

    A withdrawal after a restart carries this identity, so the catalog can tell
    which announcement the withdrawal retires.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    package: ModelAnnouncedPackage
    content_hash: str
    node_kind: EnumAnnouncedNodeKind
