# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalContractRevisionRecord."""

from __future__ import annotations

from pathlib import PurePosixPath
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent
from omnibase_core.models.events.work.model_work_goal_revised import (
    ModelWorkGoalRevised,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem


class ModelGoalContractRevisionRecord(BaseModel):
    """One immutable revision edge and its trusted source-catalog binding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_id: UUID
    revision_id: UUID
    replaces_revision_id: UUID | None = None
    repository: str
    contract_schema_version: ModelSemVer
    contract_path: PurePosixPath
    contract_source_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    contract_sha256: str
    dod_evidence: tuple[ModelContractDodItem, ...] = Field(..., min_length=1)
    authorization_policy_revision: UUID
    source_event: ModelWorkClaimRequested | ModelWorkGoalRevised
    source_envelope: ModelMessageEnvelope[ModelWorkEvent]

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator(
        "contract_schema_version", mode="before", json_schema_input_type=str
    )
    @classmethod
    def _schema_version_is_valid(cls, value: object) -> ModelSemVer:
        from omnibase_core.utils.util_contract_schema_version import (
            validate_contract_schema_version,
        )

        if isinstance(value, ModelSemVer):
            validate_contract_schema_version(value.to_string())
            return value
        if not isinstance(value, str):
            raise ValueError("contract_schema_version must be a SemVer string")
        validate_contract_schema_version(value)
        return ModelSemVer.parse(value)

    @field_serializer("contract_schema_version", when_used="json", return_type=str)
    def _serialize_schema_version(self, value: ModelSemVer) -> str:
        return value.to_string()

    @field_validator("contract_sha256")
    @classmethod
    def _digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("contract digest must use sha256:<64 lowercase hex>")
        return value

    @field_validator("contract_path")
    @classmethod
    def _path_is_repository_relative(cls, value: PurePosixPath) -> PurePosixPath:
        if (
            value.is_absolute()
            or ".." in value.parts
            or value.parts[:2] != ("contracts", "goals")
        ):
            raise ValueError(
                "contract_path must be repository-relative under contracts/goals/"
            )
        return value

    @model_validator(mode="after")
    def _opening_and_revision_edges_are_well_formed(
        self,
    ) -> ModelGoalContractRevisionRecord:
        if self.revision_id == self.goal_id:
            if self.replaces_revision_id is not None:
                raise ValueError(
                    "opening goal revision cannot replace another revision"
                )
            if not isinstance(self.source_event, ModelWorkClaimRequested):
                raise ValueError("opening revision must originate in a claim event")
            if self.source_event.goal_id != self.goal_id:
                raise ValueError("opening claim goal_id must match the revision goal")
        elif self.replaces_revision_id is None:
            raise ValueError("revised goal contract must name the replaced revision")
        elif not isinstance(self.source_event, ModelWorkGoalRevised):
            raise ValueError("appended revision must originate in a goal-revised event")

        event = self.source_event
        if (
            event.event_id != self.revision_id
            or self.source_envelope.payload != event
            or event.goal_id != self.goal_id
            or event.repository != self.repository
            or event.contract_source_commit_sha != self.contract_source_commit_sha
            or event.contract_path != self.contract_path
            or event.contract_sha256 != self.contract_sha256
            or event.contract_schema_version is None
            or event.contract_schema_version.to_string()
            != self.contract_schema_version.to_string()
            or event.dod_evidence != self.dod_evidence
            or event.authorization_policy_revision != self.authorization_policy_revision
        ):
            raise ValueError(
                "revision source event and signed envelope must exactly match the "
                "immutable contract revision record"
            )
        event_replaces = (
            None if isinstance(event, ModelWorkClaimRequested) else event.replaces
        )
        if event_replaces != self.replaces_revision_id:
            raise ValueError("revision edge must match the authenticated source event")
        if event.authorization_policy_revision is None:
            raise ValueError("source event must name its authorization policy revision")
        return self
