# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractDodItem — DoD evidence item for ticket contract governance.

OMN-10064 / OMN-9582: This model represents a single Definition of Done
evidence item as used in ModelTicketContract.dod_evidence. It is DISTINCT
from ModelDodEvidenceItem in models/contracts/ticket/model_dod_evidence_item.py,
which serves the PR-gate receipt validation path.

After Task 4 lands (OCC re-export + ModelDodCheck collision resolution),
OCC will re-export this class as its ModelDodEvidenceItem.

Field inventory (from OCC model_ticket_contract.py line 103, plus OMN-15392):
  id, description, source, linear_dod_text, checks, execution_scope, status,
  evidence_artifact

Security constraints: _MAX_STRING_LENGTH = 10000, _MAX_LIST_ITEMS = 1000.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_dod_evidence_execution_scope import (
    EnumDodEvidenceExecutionScope,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000


class ModelContractDodItem(BaseModel):
    """A single DoD evidence item for ticket contract governance.

    Maps a Definition of Done requirement to executable checks that can be
    run by the receipt gate to verify completion.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        ...,
        description="Unique identifier within the contract (e.g., 'dod-001')",
        max_length=50,
    )
    description: str = Field(
        ...,
        description="Human-readable description of the DoD requirement",
        max_length=_MAX_STRING_LENGTH,
    )
    source: Literal["linear", "manual", "generated"] = Field(
        default="generated",
        description="Where this DoD item originated",
    )
    # OMN-18056. WHICH ACCEPTANCE CRITERIA THIS ITEM CLAIMS TO COVER.
    #
    # This model owns the item-level field set the DoD verifier validates
    # contracts against, so a binding declared only on the receipt-gate model
    # would be rejected here as an unknown field. Both models carry it, for
    # the same reason and with the same meaning.
    #
    # See ModelDodEvidenceItem for the measurement that motivated it: the
    # relation between a ticket's acceptance criteria and its evidence was
    # UNDECLARABLE under `extra="forbid"`, so a green verdict could only ever
    # report how many checks passed, never which criterion any covered.
    binds_ac: tuple[str, ...] = Field(
        default=(),
        max_length=_MAX_LIST_ITEMS,
        description=(
            "Acceptance-criterion labels (`AC1`, `DoD2`) from the ticket body "
            "that this evidence item claims to prove. Empty means it claims "
            "none, which is a coverage gap rather than a pass."
        ),
    )
    linear_dod_text: str | None = Field(
        default=None,
        description="Original DoD text from Linear, if sourced from Linear",
        max_length=_MAX_STRING_LENGTH,
    )
    checks: list[ModelDodEvidenceCheck] = Field(
        default_factory=list,
        description="Executable checks that verify this DoD item",
        max_length=_MAX_LIST_ITEMS,
    )
    execution_scope: EnumDodEvidenceExecutionScope = Field(
        default=EnumDodEvidenceExecutionScope.HOSTED_AND_LOCAL,
        description=(
            "Gate audience authorized to execute this evidence item. "
            "local_done_gate items are not evaluated by hosted compliance."
        ),
    )
    status: Literal["pending", "verified", "failed", "skipped"] = Field(
        default="pending",
        description="Current verification status of this DoD item",
    )
    evidence_artifact: str | None = Field(
        default=None,
        description="Path to evidence artifact (e.g., test output, screenshot)",
        max_length=_MAX_STRING_LENGTH,
    )


__all__ = ["ModelContractDodItem"]
