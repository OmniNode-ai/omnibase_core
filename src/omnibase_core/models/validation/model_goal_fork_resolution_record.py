# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalForkResolutionRecord."""

from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)
from omnibase_core.utils.util_goal_verification import (
    compute_goal_resolution_event_sha256,
)


class ModelGoalForkResolutionRecord(BaseModel):
    """Work Ledger ruling that resolves all children of one fork point.

    The trusted history provider must source and authenticate ``authorization_event``
    from the accepted Work Ledger stream and verify its actor under the historical
    resolution policy. The event id and digest alone are not authority.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_id: UUID
    repository: str
    fork_parent_revision_id: UUID
    competing_revision_ids: tuple[UUID, ...] = Field(..., min_length=2)
    selected_revision_id: UUID
    resolution_policy_revision: UUID
    authorization_event_id: UUID
    authorization_sha256: str
    authorization_event: ModelWorkRulingRecorded
    authorization_envelope: ModelMessageEnvelope[ModelWorkRulingRecorded]

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("authorization_sha256")
    @classmethod
    def _authorization_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("authorization digest must use sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def _selection_is_one_unique_competitor(
        self,
    ) -> ModelGoalForkResolutionRecord:
        if len(set(self.competing_revision_ids)) != len(self.competing_revision_ids):
            raise ValueError("fork resolution must name each competing revision once")
        if self.selected_revision_id not in self.competing_revision_ids:
            raise ValueError("selected revision must be one of the named competitors")
        if self.fork_parent_revision_id in self.competing_revision_ids:
            raise ValueError("fork parent cannot be one of its competing heads")
        event_resolution = self.authorization_event.goal_revision_resolution
        if (
            self.authorization_event.event_id != self.authorization_event_id
            or self.authorization_envelope.payload != self.authorization_event
            or event_resolution is None
            or event_resolution.goal_id != self.goal_id
            or event_resolution.repository != self.repository
            or event_resolution.fork_parent_revision_id != self.fork_parent_revision_id
            or set(event_resolution.competing_revision_ids)
            != set(self.competing_revision_ids)
            or event_resolution.selected_revision_id != self.selected_revision_id
            or event_resolution.resolution_policy_revision
            != self.resolution_policy_revision
        ):
            raise ValueError(
                "fork resolution does not match its typed Work Ledger ruling event"
            )
        if compute_goal_resolution_event_sha256(self.authorization_event) != (
            self.authorization_sha256
        ):
            raise ValueError(
                "fork resolution digest does not match its typed Work Ledger event"
            )
        return self
