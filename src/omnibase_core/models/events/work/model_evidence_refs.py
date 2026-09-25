# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed evidence references (OMN-19620, plan T17).

What a lane cites when it records a decision-bearing act such as withdrawing a
question: pull requests, tickets, typed events and md ledger rows. Each is a
typed key, so a reader never parses prose to find the evidence. A value that
names nothing is refused: evidence that cites nothing is not evidence.
"""

from __future__ import annotations

import re
import uuid
from typing import Final

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.events.work.model_ledger_row_ref import ModelLedgerRowRef
from omnibase_core.models.events.work.model_pr_key import ModelPrKey

__all__ = ["ModelEvidenceRefs"]

_TICKET_RE: Final = re.compile(r"^OMN-[1-9][0-9]*$")


class ModelEvidenceRefs(ModelEventPayloadBase):
    """PRs, tickets, typed events and md ledger rows. Never empty. Hashable."""

    prs: frozenset[ModelPrKey] = Field(
        default_factory=frozenset, description="Pull requests, by repo and number."
    )
    tickets: frozenset[str] = Field(
        default_factory=frozenset,
        description="Linear tickets, 'OMN-<n>', upper-cased on validation.",
    )
    events: frozenset[uuid.UUID] = Field(
        default_factory=frozenset, description="Typed work events, by event_id."
    )
    ledger_rows: frozenset[ModelLedgerRowRef] = Field(
        default_factory=frozenset, description="Rows of the md ledger or its splits."
    )

    @field_validator("tickets", mode="before")
    @classmethod
    def _upper_tickets(cls, raw: object) -> object:
        if isinstance(raw, list | tuple | set | frozenset):
            return frozenset(
                item.upper() if isinstance(item, str) else item for item in raw
            )
        return raw

    @field_validator("tickets")
    @classmethod
    def _ticket_shape(cls, raw: frozenset[str]) -> frozenset[str]:
        for ticket in raw:
            if _TICKET_RE.match(ticket) is None:
                raise ValueError(f"ticket {ticket!r} is not an 'OMN-<n>' id")
        return raw

    @model_validator(mode="after")
    def _names_something(self) -> ModelEvidenceRefs:
        if not (self.prs or self.tickets or self.events or self.ledger_rows):
            raise ValueError(
                "evidence names no evidence: give at least one PR, ticket, event or "
                "ledger row"
            )
        return self

    @field_serializer("prs")
    def _serialize_prs_sorted(self, value: frozenset[ModelPrKey]) -> list[ModelPrKey]:
        return sorted(value, key=lambda key: (key.repo, key.number))

    @field_serializer("tickets")
    def _serialize_tickets_sorted(self, value: frozenset[str]) -> list[str]:
        return sorted(value, key=lambda ticket: int(ticket.removeprefix("OMN-")))

    @field_serializer("events")
    def _serialize_events_sorted(self, value: frozenset[uuid.UUID]) -> list[str]:
        return sorted(str(event_id) for event_id in value)

    @field_serializer("ledger_rows")
    def _serialize_rows_sorted(
        self, value: frozenset[ModelLedgerRowRef]
    ) -> list[ModelLedgerRowRef]:
        return sorted(value, key=lambda row: (row.path, row.line))
