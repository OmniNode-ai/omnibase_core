# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-event base payload and the partition-key contract (OMN-16177).

Work events are ordinary typed events in the existing ``onex.evt.omniclaude.*``
producer namespace. There is no ledger topic family and no ledger-specific
transport; the work ledger is a projection over this stream.

``emitted_at`` is a **display sort only**. Cross-domain global ordering is not
claimed, per the deterministic-truth doctrine's rule against assuming event
time is globally reliable — ordering within a partition comes from the
partition offset.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType

from pydantic import AwareDatetime, Field, field_validator, model_validator

from omnibase_core.enums.enum_proof_class import EnumProofClass
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.events.work.model_actor import ModelActor

__all__ = [
    "SUMMARY_MAX_LENGTH",
    "WORK_EVENT_PARTITION_KEY_FIELDS",
    "ModelWorkEventBase",
]

SUMMARY_MAX_LENGTH = 2000
"""Bound on the narrative field. Prose summarises the record; it is not it."""


class ModelWorkEventBase(ModelEventPayloadBase):
    """Fields common to every work event.

    ``event_id`` and ``emitted_at`` are both emitter-assigned with no default:
    a default factory here would let a consumer or a replay silently stamp its
    own identity and time onto someone else's record.
    """

    kind: EnumWorkEventKind = Field(
        ...,
        frozen=True,
        description="Which work-event kind this payload is. Matches event_type.",
    )
    event_id: uuid.UUID = Field(
        ...,
        description="Idempotency key. Emitter-assigned; the projection upserts on it.",
    )
    emitted_at: AwareDatetime = Field(
        ...,
        description=(
            "When the emitter recorded the event. Timezone-aware, emitter-assigned, "
            "never wall-clock-defaulted. DISPLAY SORT ONLY — ordering within a "
            "partition comes from the partition offset, never from this field."
        ),
    )
    actor: ModelActor = Field(
        ...,
        description="Who recorded it — a session or a node (discriminated on 'kind').",
    )
    actor_key: str = Field(
        default="",
        description=(
            "Flat partition key for the narrative domain, derived from 'actor'. "
            "Derived rather than nested because the emit registry resolves a "
            "partition key with a flat payload.get() and cannot walk a dotted path."
        ),
    )
    ticket_id: str | None = Field(
        default=None,
        max_length=64,
        description="Ticket this event concerns, when it concerns one.",
    )
    summary: str = Field(
        ...,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="Bounded narrative. Structured fields carry the evidence.",
    )
    proof_class: EnumProofClass | None = Field(
        default=None,
        description="Which surface proves the claim, when the event makes one.",
    )

    @field_validator("summary")
    @classmethod
    def _reject_blank_summary(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("summary must not be blank or whitespace-only")
        return raw

    @field_validator("ticket_id")
    @classmethod
    def _reject_blank_ticket_id(cls, raw: str | None) -> str | None:
        if raw is not None and not raw.strip():
            raise ValueError("ticket_id must not be blank or whitespace-only")
        return raw

    @field_validator("emitted_at")
    @classmethod
    def _reject_naive_emitted_at(cls, raw: datetime) -> datetime:
        if raw.tzinfo is None:
            raise ValueError("emitted_at must be timezone-aware")
        return raw

    @model_validator(mode="after")
    def _derive_and_check_actor_key(self) -> ModelWorkEventBase:
        """Fill ``actor_key`` from the actor, or reject one that disagrees.

        Filling it keeps callers from hand-typing a partition key. Rejecting a
        mismatch keeps a forged one from routing an event to a partition that
        contradicts the actor it names — the round-trip has to preserve the
        value, so it cannot simply be overwritten on every validation.
        """
        derived = self.actor.actor_key
        if not self.actor_key:
            object.__setattr__(self, "actor_key", derived)
            self.__pydantic_fields_set__.add("actor_key")
            return self
        if self.actor_key != derived:
            raise ValueError(
                f"actor_key {self.actor_key!r} does not match the actor it names "
                f"(expected {derived!r})"
            )
        return self


WORK_EVENT_PARTITION_KEY_FIELDS: Mapping[EnumWorkEventKind, str] = MappingProxyType(
    {
        # Arbitration domain: total order per ticket, by partition offset.
        EnumWorkEventKind.CLAIM_REQUESTED: "ticket_id",
        EnumWorkEventKind.CLAIM_RELEASED: "ticket_id",
        # Narrative domain: total order per actor, by partition offset.
        EnumWorkEventKind.RESULT_RECORDED: "actor_key",
        EnumWorkEventKind.RULING_RECORDED: "actor_key",
        EnumWorkEventKind.CORRECTION_RECORDED: "actor_key",
    }
)
"""The ``partition_key_field`` the emit registry must declare for each kind.

Two domains, because the requirements genuinely conflict: claims need a total
order per ticket so the earliest un-released claim wins arbitration, while
narrative needs a total order per actor so one lane's story stays readable.
A single key breaks one of them. Cross-domain global ordering is not claimed.

Every value here must be a flat top-level field of ``ModelWorkEventBase``:
``node_emit_daemon/event_registry.py`` resolves the key with a plain
``payload.get(field)`` and would key on ``None`` for a dotted path.
"""
