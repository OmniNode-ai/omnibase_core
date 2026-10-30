# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node announcement: one record per contract of one installed package (OMN-21589).

A package announces what it contains before any container exists. The catalog is
built from these records, so the runtime reads a catalog instead of scanning
entry points and pushing contracts to the registry. The record sits beside
``ModelContractRegisteredEvent``, which carries the contract text and a node
version and none of the package, kind, topics or dependencies the catalog needs.
"""

import hashlib
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_announced_node_kind import EnumAnnouncedNodeKind
from omnibase_core.enums.enum_announcement_operation import EnumAnnouncementOperation
from omnibase_core.models.events.contract_registration.model_announced_package import (
    ModelAnnouncedPackage,
)

_HEX = frozenset("0123456789abcdef")


class ModelNodeAnnouncement(BaseModel):
    """One contract of one installed package, announced or withdrawn.

    Attributes:
        entity_id: The contract name.
        operation: ``announce`` or ``withdraw``.
        content_hash: Canonical content hash of the contract file (64 lowercase hex).
        package: Distribution and exact installed version.
        node_kind: ``node`` or ``kernel_plugin``.
        declared_topics: Every topic the contract declares, from its own declarations.
        handler_dependencies: Protocol identifiers the contract declares, bound by overlay.
        announcer_id: The announcer that published the record.
        generation: Counter per announcer and distribution that rises with every
            announcement, so a delayed record can be told from a newer one.
        announced_at: When the announcer published the record (timezone-aware).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: str = Field(min_length=1)
    operation: EnumAnnouncementOperation
    content_hash: str = Field(min_length=64, max_length=64)
    package: ModelAnnouncedPackage
    node_kind: EnumAnnouncedNodeKind
    declared_topics: tuple[str, ...] = ()
    handler_dependencies: tuple[str, ...] = ()
    announcer_id: UUID
    generation: int = Field(ge=1)
    announced_at: datetime

    @field_validator("content_hash")
    @classmethod
    def _hash_is_lowercase_hex(cls, value: str) -> str:
        if not set(value) <= _HEX:
            raise ValueError("content_hash must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("announced_at")
    @classmethod
    def _announced_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("announced_at must be timezone-aware")
        return value

    @staticmethod
    def canonical_content_hash(raw: bytes) -> str:
        """Return the canonical content hash of a contract file's bytes.

        The canonical form is declared so a consumer with no Python can reproduce it:
        take the file's bytes as they are on disk (no YAML parse, no re-serialisation),
        turn ``\\r\\n`` and then any lone ``\\r`` into ``\\n``, SHA-256 the result and
        render it as 64 lowercase hexadecimal characters with no prefix. It is the form
        omnibase_infra's ``util_contract_content_hash`` states, so the announcement's
        hash is the one wire hash of the contract hot-loading plan; core names it here
        without importing infra.
        """
        normalised = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return hashlib.sha256(normalised).hexdigest()
