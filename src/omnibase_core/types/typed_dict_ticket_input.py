# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDictTicketInput — typed input shape for validate_ticket_contract. OMN-8916"""

from __future__ import annotations

from typing import Required, TypedDict

from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)


class TypedDictTicketInput(TypedDict, total=False):
    """Typed shape of the structured ticket dict for validate_ticket_contract.

    dod_evidence accepts ModelDodEvidenceItem instances or raw dicts (Pydantic coerces).
    """

    ticket_id: Required[str]
    title: Required[str]
    dod_evidence: Required[list[ModelDodEvidenceItem | object]]
    golden_path: Required[str]
    runtime_change: bool
    deploy_step: str | None


__all__ = ["TypedDictTicketInput"]
