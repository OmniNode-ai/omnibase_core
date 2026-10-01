# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Append-only goal-contract revision event (OMN-20028, GC.5)."""

from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.utils.util_contract_schema_version import (
    validate_contract_schema_version,
)

__all__ = ["ModelWorkGoalRevised"]


class ModelWorkGoalRevised(ModelWorkEventBase):
    """A complete replacement contract linked to the revision it supersedes."""

    kind: Literal[EnumWorkEventKind.GOAL_REVISED] = Field(
        default=EnumWorkEventKind.GOAL_REVISED, frozen=True
    )
    ticket_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional ticket correlation. It is not goal identity.",
    )
    goal_id: uuid.UUID = Field(
        ...,
        description="event_id of the opening claim for the goal being revised.",
    )
    repository: str | None = Field(
        default=None, description="Exact repository identity of a source-bound goal."
    )
    contract_source_commit_sha: str | None = Field(
        default=None,
        description="Immutable Git commit containing a source-bound goal contract.",
    )
    contract_path: PurePosixPath | None = Field(
        default=None, description="Repository-relative path to the goal contract."
    )
    contract_sha256: str | None = Field(
        default=None, description="Canonical digest of the goal contract contents."
    )
    authorization_policy_revision: uuid.UUID | None = Field(
        default=None,
        description="Protected policy revision authorizing this revision.",
    )
    dod_evidence: tuple[ModelContractDodItem, ...] = Field(
        ...,
        description="Full replacement goal contract; revisions never patch an item.",
    )
    contract_schema_version: ModelSemVer = Field(
        ...,
        description="Declared schema version bound into hashes for this goal contract.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Why the goal contract changed.",
    )
    replaces: uuid.UUID = Field(
        ...,
        description="event_id of the opening claim or revision this event supersedes.",
    )

    @field_validator("reason")
    @classmethod
    def _reject_blank_reason(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("reason must not be blank or whitespace-only")
        return raw

    @field_validator(
        "contract_schema_version", mode="before", json_schema_input_type=str
    )
    @classmethod
    def _validate_contract_schema_version(cls, value: object) -> ModelSemVer:
        if isinstance(value, ModelSemVer):
            validate_contract_schema_version(value.to_string())
            return value
        if not isinstance(value, str):
            raise ValueError("contract_schema_version must be a SemVer string")
        validate_contract_schema_version(value)
        return ModelSemVer.parse(value)

    @field_serializer("contract_schema_version", when_used="json", return_type=str)
    def _serialize_contract_schema_version(self, value: ModelSemVer) -> str:
        return value.to_string()

    @model_validator(mode="after")
    def _goal_source_fields_are_all_or_none(self) -> ModelWorkGoalRevised:
        source_fields = (
            self.repository,
            self.contract_source_commit_sha,
            self.contract_path,
            self.contract_sha256,
            self.authorization_policy_revision,
        )
        if all(value is None for value in source_fields):
            if self.ticket_id is None:
                raise ValueError("legacy goal revision requires ticket_id")
            return self
        if any(value is None for value in source_fields):
            raise ValueError("source-bound goal revision requires every source field")
        if not self.dod_evidence:
            raise ValueError("source-bound goal revision requires a non-empty contract")
        return self

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(
            r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$", value
        ):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("contract_source_commit_sha")
    @classmethod
    def _source_commit_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"^[0-9a-f]{40}$", value):
            raise ValueError(
                "contract source commit must be a full lowercase Git SHA-1"
            )
        return value

    @field_validator("contract_path")
    @classmethod
    def _contract_path_is_repository_relative(
        cls, value: PurePosixPath | None
    ) -> PurePosixPath | None:
        if value is not None and (
            value.is_absolute()
            or ".." in value.parts
            or value.parts[:2] != ("contracts", "goals")
        ):
            raise ValueError(
                "contract_path must be repository-relative under contracts/goals/"
            )
        return value

    @field_validator("contract_sha256")
    @classmethod
    def _contract_digest_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"^sha256:[0-9a-f]{64}$", value):
            raise ValueError("contract_sha256 must use sha256:<64 lowercase hex>")
        return value
