# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The verdict of the ticket-creation admission check (OMN-22850)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ticket_creation.model_ticket_creation_finding import (
    ModelTicketCreationFinding,
)


class ModelTicketCreationCheckResult(BaseModel):
    """Every failing rule for one payload; an empty tuple admits it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelTicketCreationFinding, ...] = Field(
        default=(), description="Failing rules, in rule order"
    )

    @property
    def admitted(self) -> bool:
        """True when no rule failed."""
        return not self.findings

    @property
    def codes(self) -> tuple[str, ...]:
        """The finding codes, in order."""
        return tuple(finding.code for finding in self.findings)
