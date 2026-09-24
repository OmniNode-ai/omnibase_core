# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The folded state of a work ledger (OMN-19405, typed work ledger T4).

The output of the work-ledger fold COMPUTE node and the only input of the
queries. It is a function of the SET of events in the ledger: every tuple is in
a canonical order, so any permutation or duplication of the ledger's lines
folds to the same state apart from ``line_count``.
"""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_ledger_epoch_opened import (
    ModelWorkLedgerEpochOpened,
)
from omnibase_core.models.events.work.model_work_message_acked import (
    ModelWorkMessageAcked,
)
from omnibase_core.models.events.work.model_work_message_sent import (
    ModelWorkMessageSent,
)
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)
from omnibase_core.models.nodes.work_ledger_state.model_invalid_release import (
    ModelInvalidRelease,
)

__all__ = ["ModelWorkLedgerState"]


class ModelWorkLedgerState(BaseModel):
    """Holds in force, open claims, messages and acks, and every reason for doubt."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line_count: int = Field(..., ge=0, description="Lines the fold was given.")
    event_count: int = Field(
        ..., ge=0, description="Distinct event_ids among the lines that parsed."
    )
    undecided_reasons: tuple[str, ...] = Field(
        default=(),
        description=(
            "Every reason the ledger cannot be decided from, sorted. Non-empty "
            "means every query answers UNDECIDED."
        ),
    )
    epoch: ModelWorkLedgerEpochOpened | None = Field(
        default=None,
        description="The newest epoch event (highest epoch_seq), or None before the cutover.",
    )
    last_event_at: AwareDatetime | None = Field(
        default=None, description="Latest emitted_at among the events. Display only."
    )
    holds_in_force: tuple[ModelHoldInForce, ...] = Field(
        default=(), description="Holds not wholly released, sorted by event_id."
    )
    invalid_releases: tuple[ModelInvalidRelease, ...] = Field(
        default=(), description="Releases that released nothing, sorted by event_id."
    )
    open_claims: tuple[ModelWorkClaimRequested, ...] = Field(
        default=(),
        description="Claims neither released nor closed, sorted by event_id.",
    )
    messages: tuple[ModelWorkMessageSent, ...] = Field(
        default=(), description="Every message, sorted by event_id."
    )
    acks: tuple[ModelWorkMessageAcked, ...] = Field(
        default=(), description="Every acknowledgement, sorted by event_id."
    )

    @property
    def decidable(self) -> bool:
        """True when no reason for doubt was found."""
        return not self.undecided_reasons
