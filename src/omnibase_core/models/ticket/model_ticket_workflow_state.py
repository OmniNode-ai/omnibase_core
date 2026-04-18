# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTicketWorkflowState — mutable FSM state for the ticket-work handler.

Distinct from ``ModelTicketContract`` (the canonical Linear ticket contract that
carries dod_evidence, golden_path, etc.). ``ModelTicketWorkflowState`` tracks the
handler's in-flight workflow: the phase it is in, the clarifying questions it has
posed, the requirements/verification/gates it has declared, and the commits/PR it
has produced. It is serialized to YAML and embedded in the Linear ticket
description so the handler can resume across sessions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_ticket_workflow_phase import (
    EnumTicketWorkflowPhase,
)
from omnibase_core.models.ticket.model_workflow_context import ModelWorkflowContext
from omnibase_core.models.ticket.model_workflow_gate import ModelWorkflowGate
from omnibase_core.models.ticket.model_workflow_question import ModelWorkflowQuestion
from omnibase_core.models.ticket.model_workflow_requirement import (
    ModelWorkflowRequirement,
)
from omnibase_core.models.ticket.model_workflow_verification import (
    ModelWorkflowVerification,
)


class ModelTicketWorkflowState(BaseModel):
    """Mutable FSM state for the ticket-work handler, persisted to Linear.

    Serialized into the ``## Contract`` YAML block of the Linear ticket
    description so the handler can resume a ticket across sessions.

    Phase values are strings (via ``EnumTicketWorkflowPhase``) rather than the
    canonical ``EnumTicketPhase`` because the wire format pre-dates the
    canonical contract model and would break resume on existing tickets if
    changed — ``IMPLEMENTATION`` vs ``IMPLEMENT`` in particular. The two
    enums are intentionally distinct.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(default="")
    title: str = Field(default="")
    repo: str = Field(default="")
    branch: str | None = Field(default=None)

    phase: EnumTicketWorkflowPhase = Field(default=EnumTicketWorkflowPhase.INTAKE)
    created_at: str = Field(default="")
    updated_at: str = Field(default="")

    context: ModelWorkflowContext = Field(default_factory=ModelWorkflowContext)

    questions: list[ModelWorkflowQuestion] = Field(default_factory=list)

    requirements: list[ModelWorkflowRequirement] = Field(default_factory=list)
    verification: list[ModelWorkflowVerification] = Field(default_factory=list)
    gates: list[ModelWorkflowGate] = Field(default_factory=list)

    commits: list[str] = Field(default_factory=list)
    pr_url: str | None = Field(default=None)
    hardening_tickets: list[str] = Field(default_factory=list)

    def is_questions_complete(self) -> bool:
        """All required questions have non-empty answers."""
        return all(q.answer and q.answer.strip() for q in self.questions if q.required)

    def is_spec_complete(self) -> bool:
        """At least one requirement, and every requirement has acceptance criteria."""
        if not self.requirements:
            return False
        return all(len(r.acceptance) > 0 for r in self.requirements)

    def is_verification_complete(self) -> bool:
        """All blocking verification passed or skipped."""
        return all(
            v.status in ("passed", "skipped") for v in self.verification if v.blocking
        )

    def is_gates_complete(self) -> bool:
        """All required gates approved."""
        return all(g.status == "approved" for g in self.gates if g.required)

    def is_done(self) -> bool:
        """Workflow reached DONE and all completion checks pass."""
        return (
            self.phase == EnumTicketWorkflowPhase.DONE
            and self.is_questions_complete()
            and self.is_spec_complete()
            and self.is_verification_complete()
            and self.is_gates_complete()
        )


__all__ = ["ModelTicketWorkflowState"]
