# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkflowGate — human or policy gate in the ticket-work state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_ticket_types import (
    EnumGateKind,
    EnumTicketStepStatus,
)


class ModelWorkflowGate(BaseModel):
    """A human or policy gate declared during the SPEC phase."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="")
    title: str = Field(default="")
    kind: EnumGateKind = Field(default=EnumGateKind.HUMAN_APPROVAL)
    required: bool = Field(default=True)
    status: EnumTicketStepStatus = Field(default=EnumTicketStepStatus.PENDING)
    notes: str | None = Field(default=None)
    resolved_at: str | None = Field(default=None)


__all__ = ["ModelWorkflowGate"]
