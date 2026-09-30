# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Append-only goal-contract revision event (OMN-20028, GC.5)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, field_serializer, field_validator

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
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Ticket partition shared with the opening claim.",
    )
    goal_id: uuid.UUID = Field(
        ...,
        description="event_id of the opening claim for the goal being revised.",
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
