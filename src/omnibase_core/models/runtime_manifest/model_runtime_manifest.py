# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.runtime_manifest.model_manifest_contract import (
    ModelManifestContract,
)
from omnibase_core.models.runtime_manifest.model_manifest_handler import (
    ModelManifestHandler,
)
from omnibase_core.models.runtime_manifest.model_ownership_violation import (
    ModelOwnershipViolation,
)


class ModelRuntimeManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    runtime_profile: str = Field(..., min_length=1)
    contracts: tuple[ModelManifestContract, ...] = Field(default=())
    owned_command_topics: frozenset[str] = Field(default_factory=frozenset)
    subscribed_event_topics: frozenset[str] = Field(default_factory=frozenset)
    handlers: tuple[ModelManifestHandler, ...] = Field(default=())
    skipped_contracts: tuple[ModelManifestContract, ...] = Field(default=())
    failed_contracts: tuple[ModelManifestContract, ...] = Field(default=())
    ownership_violations: tuple[ModelOwnershipViolation, ...] = Field(default=())
    image_digest: str | None = Field(default=None)
    started_at: datetime = Field(...)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def contract_hash(self) -> str:
        sorted_hashes = sorted(c.contract_hash for c in self.contracts)
        payload = json.dumps(sorted_hashes, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def topology_hash(self) -> str:
        payload = json.dumps(
            {
                "runtime_profile": self.runtime_profile,
                "contract_hash": self.contract_hash,
                "owned_command_topics": sorted(self.owned_command_topics),
                "subscribed_event_topics": sorted(self.subscribed_event_topics),
                "handlers": sorted(h.name for h in self.handlers),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


__all__ = ["ModelRuntimeManifest"]
