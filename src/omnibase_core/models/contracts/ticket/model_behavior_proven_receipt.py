# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelBehaviorProvenReceipt — proof artifact for behavior_proven DoD evidence.

Parent epic: OMN-9277. Sibling: OMN-9279 (DoD guard), OMN-9280 (scaffold
skill), OMN-9281 (pre-merge CI gate).

A behavior_proven receipt asserts that a ticket's handler / pipeline /
consumer / effect work was exercised against live external state, not
merely unit-tested. Tickets labelled handler/pipeline/consumer/effect
cannot close Done without a passing receipt (see OMN-9279).

The receipt is a discriminated sibling of :class:`ModelDodReceipt`; both
are recognised by the receipt-gate. `behavior_proven` is registered as a
first-class ``check_type`` via :const:`BEHAVIOR_PROVEN_CHECK_TYPE` so
existing :class:`ModelDodEvidenceItem` YAML contracts accept it without
schema migration.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.ticket.enum_behavior_proven_assertion import (
    EnumBehaviorProvenAssertion,
)

BEHAVIOR_PROVEN_CHECK_TYPE = "behavior_proven"

_TICKET_ID_RE = re.compile(r"^OMN-\d+$")


class ModelBehaviorProvenReceipt(BaseModel):
    """Receipt proving a behavior_proven DoD check ran against live state.

    Frozen. Every field except ``observed_state`` is required — a receipt
    that doesn't record what was run, what was queried, and what was
    observed is worthless as proof. Treated identically to absence by
    the DoD guard (OMN-9279) and the CI gate (OMN-9281).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    ticket_id: str = Field(
        ..., description="Linear ticket this receipt proves (e.g., OMN-9214)"
    )
    # string-id-ok: evidence item IDs are human-readable slugs from contract YAML
    evidence_item_id: str = Field(
        ...,
        min_length=1,
        description="dod_evidence[].id this receipt covers",
    )
    command_run: str = Field(
        ...,
        min_length=1,
        description=(
            "The exact command executed to exercise the behavior "
            "(e.g., 'kcat -P -b ... -t onex.cmd.merge_sweep.v1')."
        ),
    )
    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Live-state query used to observe the effect "
            "(e.g., 'rpk topic consume onex.evt.merge_sweep.completed.v1')."
        ),
    )
    assertion: EnumBehaviorProvenAssertion = Field(
        ...,
        description="passed or failed — absence is treated identically to failed",
    )
    observed_at: datetime = Field(
        ..., description="UTC timestamp when the live state was observed"
    )
    observed_state: str | None = Field(
        default=None,
        description=(
            "Truncated observed state (stdout, query body, rendered snapshot). "
            "Large payloads should be stored in a sibling file and referenced "
            "here by path. None is allowed when the probe produced no output."
        ),
    )

    @field_validator("ticket_id")
    @classmethod
    def _validate_ticket_id(cls, v: str) -> str:
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"ticket_id must match OMN-\\d+, got: {v!r}")
        return v

    @field_validator("observed_at")
    @classmethod
    def _validate_tz_aware(cls, v: Any) -> datetime:
        if not isinstance(v, datetime):
            raise ValueError(f"observed_at must be datetime, got {type(v).__name__}")
        if v.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware (UTC)")
        return v.astimezone(UTC)


__all__ = [
    "BEHAVIOR_PROVEN_CHECK_TYPE",
    "ModelBehaviorProvenReceipt",
]
