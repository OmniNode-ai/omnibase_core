# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-requested work event (OMN-16177)."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    ModelWorkEventBase,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.utils.util_contract_schema_version import (
    validate_contract_schema_version,
)

__all__ = ["ModelWorkClaimRequested"]


class ModelWorkClaimRequested(ModelWorkEventBase):
    """Open a legacy ticket claim or an explicitly source-bound goal.

    Legacy mode requires ``ticket_id`` and preserves that exact arbitration key.
    Goal mode requires the complete source tuple and uses repository+goal identity;
    a ticket, when present, is correlation only.
    """

    kind: Literal[EnumWorkEventKind.CLAIM_REQUESTED] = Field(
        default=EnumWorkEventKind.CLAIM_REQUESTED, frozen=True
    )
    ticket_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional ticket correlation. It is not goal identity.",
    )
    goal_id: uuid.UUID | None = Field(
        default=None,
        description="Opening goal identity; must equal this event's event_id.",
    )
    repository: str | None = Field(
        default=None,
        description="Exact repository identity bound by the goal contract.",
    )
    contract_source_commit_sha: str | None = Field(
        default=None, description="Immutable Git commit containing the goal contract."
    )
    contract_path: PurePosixPath | None = Field(
        default=None, description="Repository-relative path to the goal contract."
    )
    contract_sha256: str | None = Field(
        default=None, description="Canonical digest of the goal contract contents."
    )
    authorization_policy_revision: uuid.UUID | None = Field(
        default=None,
        description="Protected policy revision authorizing this goal opening.",
    )
    dod_evidence: tuple[ModelContractDodItem, ...] = Field(
        default=(),
        description=(
            "The goal contract opened by this claim. Empty remains valid for legacy "
            "claims written before goal contracts were added."
        ),
    )
    contract_schema_version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Declared schema version bound into hashes for this goal contract. "
            "Legacy claims without a contract omit it."
        ),
    )
    parent_goal_id: uuid.UUID | None = Field(
        default=None,
        description="Opening claim event_id of the parent goal, when this is a child.",
    )
    prs: frozenset[ModelPrKey] = Field(
        default_factory=frozenset,
        description="Pull requests the claim covers, keyed by repo and number.",
    )
    scope_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="What the claim covers and excludes, for humans. Never read by a checker.",
    )
    est_lane_hours: Decimal | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description="Estimated cost of the claimed work, in lane-hours (rule 4).",
    )
    displaces: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="What this work displaces (rule 4). Display only.",
    )
    consent_ref: uuid.UUID | None = Field(
        default=None,
        description="event_id of the work.consent.recorded that authorizes this work.",
    )

    @field_validator(
        "contract_schema_version",
        mode="before",
        json_schema_input_type=str | None,
    )
    @classmethod
    def _validate_contract_schema_version(cls, value: object) -> ModelSemVer | None:
        if value is None:
            return None
        if isinstance(value, ModelSemVer):
            validate_contract_schema_version(value.to_string())
            return value
        if not isinstance(value, str):
            raise ValueError("contract_schema_version must be a SemVer string")
        validate_contract_schema_version(value)
        return ModelSemVer.parse(value)

    @model_validator(mode="after")
    def _require_schema_version_for_goal_contract(self) -> ModelWorkClaimRequested:
        if self.dod_evidence and self.contract_schema_version is None:
            raise ValueError(
                "contract_schema_version is required when dod_evidence is present"
            )
        goal_source_fields = (
            self.repository,
            self.contract_source_commit_sha,
            self.contract_path,
            self.contract_sha256,
            self.authorization_policy_revision,
        )
        if self.goal_id is None:
            if any(value is not None for value in goal_source_fields):
                raise ValueError("goal contract source fields require goal_id")
            if self.ticket_id is None:
                raise ValueError("legacy claim requires ticket_id")
            return self
        if self.goal_id != self.event_id:
            raise ValueError("opening goal_id must equal the claim event_id")
        if any(value is None for value in goal_source_fields) or (
            self.contract_schema_version is None
        ):
            raise ValueError("goal opening requires every source and policy field")
        if not self.dod_evidence:
            raise ValueError("goal opening requires a non-empty contract")
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

    @field_serializer("prs")
    def _serialize_prs_sorted(self, value: frozenset[ModelPrKey]) -> list[ModelPrKey]:
        return sorted(value, key=lambda key: (key.repo, key.number))

    @field_serializer(
        "contract_schema_version", when_used="json", return_type=str | None
    )
    def _serialize_contract_schema_version(
        self, value: ModelSemVer | None
    ) -> str | None:
        return value.to_string() if value is not None else None
