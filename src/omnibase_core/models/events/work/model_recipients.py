# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Who a work event is addressed to (OMN-16177, typed work ledger)."""

from __future__ import annotations

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelRecipients"]


class ModelRecipients(ModelEventPayloadBase):
    """Named lanes, every lane, the operator, or any combination. Never nobody."""

    lanes: frozenset[str] = Field(
        default_factory=frozenset,
        description="Lane names the event is addressed to.",
    )
    all_lanes: bool = Field(
        default=False, description="Addressed to every lane (the old to=all)."
    )
    operator: bool = Field(default=False, description="Addressed to the operator.")

    @field_validator("lanes")
    @classmethod
    def _reject_blank_lanes(cls, raw: frozenset[str]) -> frozenset[str]:
        for lane in raw:
            if not lane.strip() or len(lane) > 128:
                raise ValueError(
                    f"lane name {lane!r} must be non-blank and at most 128 characters"
                )
        return raw

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
