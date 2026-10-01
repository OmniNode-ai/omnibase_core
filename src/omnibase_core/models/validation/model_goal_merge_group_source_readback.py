# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected current-source readback for a retained merge-group delivery."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_goal_admission import _REPOSITORY_RE


class ModelGoalMergeGroupSourceReadback(BaseModel):
    """Retained webhook identity cross-checked with current GitHub group state.

    The protected provider selects the immutable retained delivery by the
    observation's delivery ID, verifies its original HMAC and broker checkpoint,
    and freshly reads current group refs, commit SHAs, and trees before returning
    this model. Core compares every field with the recorded observation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    contract_revision: UUID
    delivery_id: UUID
    merge_group_id: str = Field(  # string-id-ok: GitHub merge-group head-ref identity
    )
    merge_group_ref: str
    base_ref: str
    head_ref: str
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_tree_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    head_tree_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_checkpoint_id: str = Field(  # string-id-ok: Kafka checkpoint
        min_length=1, max_length=512
    )
    source_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    received_at: datetime
    observed_at: datetime

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _retained_and_current_identity_are_consistent(
        self,
    ) -> ModelGoalMergeGroupSourceReadback:
        if not all(
            (self.merge_group_id, self.merge_group_ref, self.base_ref, self.head_ref)
        ):
            raise ValueError("merge-group readback requires exact group and refs")
        if (
            self.merge_group_id != self.head_ref
            or self.merge_group_ref != self.head_ref
        ):
            raise ValueError("merge-group identity must equal the exact head ref")
        for name in ("received_at", "observed_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a timezone")
        if self.observed_at < self.received_at:
            raise ValueError("current readback cannot precede retained delivery")
        return self


__all__ = ["ModelGoalMergeGroupSourceReadback"]
