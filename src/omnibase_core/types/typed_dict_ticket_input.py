# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDictTicketInput — typed input shape for validate_ticket_contract. OMN-8916"""

from __future__ import annotations

from typing import Required, TypedDict


class TypedDictTicketInput(TypedDict, total=False):
    """Typed shape of the structured ticket dict for validate_ticket_contract.

    dod_evidence accepts ModelDodEvidenceItem instances or raw dicts (Pydantic coerces).
    """

    ticket_id: Required[str]
    title: Required[str]
    # OMN-14337: element type was <dod-evidence domain model> | object (already
    # object-absorbed); dropped the import to sever the runtime types->models edge.
    dod_evidence: Required[list[object]]
    golden_path: Required[str]
    runtime_change: bool
    deploy_step: str | None


__all__ = ["TypedDictTicketInput"]
