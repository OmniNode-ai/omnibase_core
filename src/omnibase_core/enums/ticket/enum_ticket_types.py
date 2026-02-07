"""Enum type definitions for ticket-driven workflow.

Provides phase, action, status, and kind enumerations for the
TicketContract model and related workflow automation.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTicketPhase(StrValueHelper, str, Enum):
    """Workflow phases for ticket processing."""

    INTAKE = "intake"
    RESEARCH = "research"
    QUESTIONS = "questions"
    SPEC = "spec"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    DONE = "done"


@unique
class EnumTicketAction(StrValueHelper, str, Enum):
    """Actions that can be performed during ticket processing."""

    FETCH_TICKET = "fetch_ticket"
    PARALLEL_SOLVE = "parallel_solve"
    ASK_QUESTION = "ask_question"
    EDIT_REQUIREMENTS = "edit_requirements"
    EDIT_VERIFICATION = "edit_verification"
    MODIFY_CODE = "modify_code"
    COMMIT = "commit"
    RUN_VERIFICATION = "run_verification"
    OPEN_HARDENING_TICKET = "open_hardening_ticket"


@unique
class EnumTicketStepStatus(StrValueHelper, str, Enum):
    """Status values for ticket verification steps and gates."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    APPROVED = "approved"
    REJECTED = "rejected"


@unique
class EnumVerificationKind(StrValueHelper, str, Enum):
    """Types of verification steps."""

    UNIT_TESTS = "unit_tests"
    LINT = "lint"
    MYPY = "mypy"
    INTEGRATION = "integration"
    MANUAL_CHECK = "manual_check"
    SCRIPT = "script"
    VERIFY_INTERFACE = "verify_interface"


@unique
class EnumGateKind(StrValueHelper, str, Enum):
    """Types of gates that require approval."""

    HUMAN_APPROVAL = "human_approval"
    POLICY_CHECK = "policy_check"
    SECURITY_CHECK = "security_check"


# Phase to action mapping
PHASE_ALLOWED_ACTIONS: dict[EnumTicketPhase, frozenset[EnumTicketAction]] = {
    EnumTicketPhase.INTAKE: frozenset({EnumTicketAction.FETCH_TICKET}),
    EnumTicketPhase.RESEARCH: frozenset({EnumTicketAction.PARALLEL_SOLVE}),
    EnumTicketPhase.QUESTIONS: frozenset(
        {
            EnumTicketAction.ASK_QUESTION,
            EnumTicketAction.EDIT_REQUIREMENTS,
        }
    ),
    EnumTicketPhase.SPEC: frozenset(
        {
            EnumTicketAction.EDIT_REQUIREMENTS,
            EnumTicketAction.EDIT_VERIFICATION,
        }
    ),
    EnumTicketPhase.IMPLEMENTATION: frozenset(
        {
            EnumTicketAction.MODIFY_CODE,
            EnumTicketAction.COMMIT,
            EnumTicketAction.RUN_VERIFICATION,
        }
    ),
    EnumTicketPhase.REVIEW: frozenset(
        {
            EnumTicketAction.RUN_VERIFICATION,
            EnumTicketAction.OPEN_HARDENING_TICKET,
        }
    ),
    EnumTicketPhase.DONE: frozenset(),
}

# Aliases for cleaner imports (match requirement spec naming)
Phase = EnumTicketPhase
Action = EnumTicketAction
Status = EnumTicketStepStatus
VerificationKind = EnumVerificationKind
GateKind = EnumGateKind

__all__ = [
    # Enum types (canonical names)
    "EnumTicketPhase",
    "EnumTicketAction",
    "EnumTicketStepStatus",
    "EnumVerificationKind",
    "EnumGateKind",
    # Aliases for cleaner API
    "Phase",
    "Action",
    "Status",
    "VerificationKind",
    "GateKind",
    # Constants
    "PHASE_ALLOWED_ACTIONS",
]
