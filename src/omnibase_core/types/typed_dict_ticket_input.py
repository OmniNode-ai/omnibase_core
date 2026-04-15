# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDictTicketInput — typed input shape for validate_ticket_contract. OMN-8916"""

from __future__ import annotations

from typing import Required, TypedDict


class TypedDictTicketInput(TypedDict, total=False):
    """Typed shape of the ticket dict accepted by validate_ticket_contract."""

    ticket_id: Required[str]
    title: Required[str]
    dod_evidence: Required[list[object]]
    golden_path: Required[str]
    runtime_change: bool
    deploy_step: str | None


__all__ = ["TypedDictTicketInput"]
