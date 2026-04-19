# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumTicketWorkflowPhase — phase strings persisted in ticket-work workflow state.

Distinct from ``EnumTicketPhase`` (which drives the contract-action mapping in
``enum_ticket_types``): workflow-phase values are the *wire format* written into
Linear ticket descriptions by the ticket-work handler, so string values must
match the historical on-disk format exactly.
"""

from __future__ import annotations

from enum import StrEnum


class EnumTicketWorkflowPhase(StrEnum):
    """Phases of the ticket-work handler FSM.

    Values are the exact strings persisted to Linear ticket YAML contracts —
    changing them breaks resume-on-existing-ticket paths.
    """

    INTAKE = "intake"
    RESEARCH = "research"
    QUESTIONS = "questions"
    SPEC = "spec"
    IMPLEMENT = "implement"
    REVIEW = "review"
    DONE = "done"


__all__ = ["EnumTicketWorkflowPhase"]
