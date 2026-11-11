# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A ticket contract before the tracker has assigned an id (OMN-23758)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_completeness import EnumContractCompleteness
from omnibase_core.enums.enum_proof_class import EnumProofClass
from omnibase_core.enums.ticket.enum_contract_interface_surface import (
    EnumContractInterfaceSurface,
)
from omnibase_core.models.ticket.model_contract_dod_item import (
    ModelContractDodItem,
)
from omnibase_core.models.ticket.model_emergency_bypass import (
    ModelEmergencyBypass,
)
from omnibase_core.models.ticket.model_evidence_requirement import (
    ModelEvidenceRequirement,
)
from omnibase_core.models.ticket.model_golden_path import ModelGoldenPath
from omnibase_core.models.ticket.model_requirement import ModelRequirement
from omnibase_core.models.ticket.model_ticket_business_brief import (
    ModelTicketBusinessBrief,
)
from omnibase_core.models.ticket.model_ticket_standard_form_fields import (
    TicketIdentifier,
)

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000
_MAX_DOD_EVIDENCE_ITEMS = 10000


class ModelTicketDraft(BaseModel):
    """A ticket contract before the tracker has assigned an id (schema 1.1.0)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_STRING_LENGTH,
        description="The ticket title; must be non-empty",
    )
    business_brief: ModelTicketBusinessBrief = Field(
        ...,
        description=(
            "The five plain-language headings: what this is, why it matters, "
            "done looks like, risk, depends on"
        ),
    )
    parent_ticket_id: TicketIdentifier = Field(
        ...,
        description="The parent ticket this one serves (the Gate line)",
    )
    parent_ac_label: str = Field(
        ...,
        description=("The parent's acceptance-criterion label this ticket serves"),
    )
    repository: str = Field(
        ...,
        min_length=1,
        description="The one repository this ticket's work belongs to",
    )
    requirements: list[ModelRequirement] = Field(
        ...,
        max_length=_MAX_LIST_ITEMS,
        description="The requirements, each with its acceptance criteria",
    )
    dod_evidence: list[ModelContractDodItem] = Field(
        ...,
        min_length=1,
        max_length=_MAX_DOD_EVIDENCE_ITEMS,
        description=(
            "DoD evidence items, each binding executable checks to the "
            "acceptance-criterion labels they prove"
        ),
    )
    description: str = Field(
        default="",
        max_length=_MAX_STRING_LENGTH,
        description="Ticket description",
    )
    summary: str = Field(
        default="",
        max_length=_MAX_STRING_LENGTH,
        description="Human-readable summary of the ticket",
    )
    start_probe: str | None = Field(
        default=None,
        description="The probe that shows the work started (a ticket created In Progress); None otherwise",
    )
    diagnosis: str | None = Field(
        default=None,
        description="The diagnosis a defect-shaped ticket cites; None otherwise",
    )
    is_seam_ticket: bool = Field(
        default=False,
        description="Whether this ticket touches cross-repo interfaces",
    )
    interface_change: bool = Field(
        default=False,
        description="Whether this ticket changes interface surfaces",
    )
    interfaces_touched: list[EnumContractInterfaceSurface] = Field(
        default_factory=list,
        max_length=_MAX_LIST_ITEMS,
        description="Interface surfaces touched by this ticket",
    )
    evidence_requirements: list[ModelEvidenceRequirement] = Field(
        default_factory=list,
        max_length=_MAX_LIST_ITEMS,
        description="Evidence requirements for ticket completion",
    )
    emergency_bypass: ModelEmergencyBypass | None = Field(
        default=None,
        description="Emergency bypass configuration (None = not configured)",
    )
    golden_path: ModelGoldenPath | None = Field(
        default=None,
        description="Optional golden path event chain test declaration",
    )
    proof_class: EnumProofClass | None = Field(
        default=None,
        description=(
            "Which surface proves this ticket's completion claim: "
            "code-only | receipt-bound | deployed | live-readback | "
            "replay-proven | prod-proven. None when not yet declared."
        ),
    )
    contract_completeness: EnumContractCompleteness = Field(
        default=EnumContractCompleteness.STUB,
        description="Completeness level of this contract",
    )


__all__ = ["ModelTicketDraft"]
