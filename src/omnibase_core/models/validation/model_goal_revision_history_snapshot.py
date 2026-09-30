# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalRevisionHistorySnapshot."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.validation.model_goal_contract_revision_record import (
    ModelGoalContractRevisionRecord,
)
from omnibase_core.models.validation.model_goal_fork_resolution_record import (
    ModelGoalForkResolutionRecord,
)
from omnibase_core.models.validation.model_goal_revision_authorization_policy import (
    ModelGoalRevisionAuthorizationPolicy,
)


class ModelGoalRevisionHistorySnapshot(BaseModel):
    """Trusted complete goal revision DAG and its authorized fork resolutions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    store_revision: UUID
    revisions: tuple[ModelGoalContractRevisionRecord, ...] = Field(..., min_length=1)
    fork_resolutions: tuple[ModelGoalForkResolutionRecord, ...] = Field(
        default_factory=tuple
    )
    revision_authorization_policies: tuple[
        ModelGoalRevisionAuthorizationPolicy, ...
    ] = Field(default_factory=tuple)
    snapshot_sha256: str

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("snapshot_sha256")
    @classmethod
    def _snapshot_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("snapshot digest must use sha256:<64 lowercase hex>")
        return value

    def content_sha256(self) -> str:
        """Digest all source edges and fork resolutions in canonical order."""
        payload = {
            "repository": self.repository,
            "goal_id": str(self.goal_id),
            "store_revision": str(self.store_revision),
            "revisions": [
                record.model_dump(mode="json")
                for record in sorted(
                    self.revisions, key=lambda record: str(record.revision_id)
                )
            ],
            "fork_resolutions": [
                {
                    **resolution.model_dump(mode="json"),
                    "competing_revision_ids": sorted(
                        str(revision_id)
                        for revision_id in resolution.competing_revision_ids
                    ),
                }
                for resolution in sorted(
                    self.fork_resolutions,
                    key=lambda resolution: (
                        str(resolution.fork_parent_revision_id),
                        str(resolution.authorization_event_id),
                    ),
                )
            ],
            "revision_authorization_policies": [
                policy.model_dump(mode="json")
                for policy in sorted(
                    self.revision_authorization_policies,
                    key=lambda policy: str(policy.policy_revision),
                )
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
