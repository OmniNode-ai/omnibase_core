# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The answer to one work-ledger query (OMN-19405, typed work ledger T4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_message_sent import (
    ModelWorkMessageSent,
)
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)

__all__ = ["ModelWorkLedgerVerdict"]


class ModelWorkLedgerVerdict(BaseModel):
    """A status plus every hold, claim or message that produced it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: EnumWorkLedgerVerdictStatus = Field(..., description="The answer.")
    holds: tuple[ModelHoldInForce, ...] = Field(
        default=(), description="Holds in force that match the question."
    )
    claims: tuple[ModelWorkClaimRequested, ...] = Field(
        default=(), description="Open claims that match the question."
    )
    messages: tuple[ModelWorkMessageSent, ...] = Field(
        default=(), description="Unacknowledged messages that match the question."
    )
    undecided_reasons: tuple[str, ...] = Field(
        default=(), description="Why the answer is UNDECIDED, when it is."
    )

    @property
    def exit_code(self) -> int:
        """0 for CLEAR, 3 for HELD or FOUND, 2 for UNDECIDED."""
        if self.status is EnumWorkLedgerVerdictStatus.CLEAR:
            return 0
        if self.status is EnumWorkLedgerVerdictStatus.UNDECIDED:
            return 2
        return 3
