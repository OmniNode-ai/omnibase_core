# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-requested work event (OMN-16177)."""

from __future__ import annotations

import uuid
from decimal import Decimal
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
    """A claimant asks to own a ticket.

    ``ticket_id`` is narrowed to required: it is this kind's partition key, and
    a null key cannot arbitrate.
    """

    kind: Literal[EnumWorkEventKind.CLAIM_REQUESTED] = Field(
        default=EnumWorkEventKind.CLAIM_REQUESTED, frozen=True
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Ticket being claimed. Required — this is the partition key.",
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
        return self

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
