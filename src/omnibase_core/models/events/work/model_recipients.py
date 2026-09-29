# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Who a work event is addressed to (OMN-16177, typed work ledger)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.events.work.model_work_name_rules import (
    LANE_NAME_PATTERN,
    normalize_work_names,
)

__all__ = ["ModelRecipients"]


class ModelRecipients(ModelEventPayloadBase):
    """Named lanes, every lane, the operator, or any combination. Never nobody."""

    lanes: frozenset[Annotated[str, Field(pattern=LANE_NAME_PATTERN)]] = Field(
        default_factory=frozenset,
        description="Lane names the event is addressed to, stripped and lower-cased.",
    )
    all_lanes: bool = Field(
        default=False, description="Addressed to every lane (the old to=all)."
    )
    operator: bool = Field(default=False, description="Addressed to the operator.")

    @field_validator("lanes", mode="before")
    @classmethod
    def _normalise_lanes(cls, raw: object) -> object:
        """Strip and lower-case before the pattern check, as repos are."""
        return normalize_work_names(raw)

    @model_validator(mode="after")
    def _names_someone(self) -> ModelRecipients:
        if not (self.lanes or self.all_lanes or self.operator):
            raise ValueError(
                "recipients must name at least one lane, all_lanes, or the operator"
            )
        return self

    @field_serializer("lanes")
    def _serialize_sorted(self, value: frozenset[str]) -> list[str]:
        return sorted(value)
