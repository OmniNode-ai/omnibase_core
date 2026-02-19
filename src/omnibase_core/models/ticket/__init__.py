# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ticket contract models for contract-driven ticket execution.

This module provides the foundation for the /ticket-work skill automation system.
It defines workflow phases, allowed actions, verification steps, and gates
for structured ticket processing.

Example:
    >>> from omnibase_core.models.ticket import (
    ...     TicketContract, Phase, Action, Status,
    ...     ClarifyingQuestion, Requirement, VerificationStep, Gate,
    ... )
    >>> contract = TicketContract(
    ...     ticket_id="OMN-1807",
    ...     title="Implement ticket contract model",
    ... )
    >>> contract.phase
    <EnumTicketPhase.INTAKE: 'intake'>
    >>> contract.allowed_actions()
    {<EnumTicketAction.FETCH_TICKET: 'fetch_ticket'>}
"""

from omnibase_core.enums.ticket import (
    PHASE_ALLOWED_ACTIONS,
    Action,
    EnumGateKind,
    EnumTicketAction,
    EnumTicketPhase,
    EnumTicketStepStatus,
    EnumVerificationKind,
    GateKind,
    Phase,
    Status,
    VerificationKind,
)
from omnibase_core.models.ticket.model_clarifying_question import (
    ClarifyingQuestion,
    ModelClarifyingQuestion,
)
from omnibase_core.models.ticket.model_gate import (
    Gate,
    ModelGate,
)
from omnibase_core.models.ticket.model_interface_consumed import (
    InterfaceConsumed,
    ModelInterfaceConsumed,
)
from omnibase_core.models.ticket.model_interface_provided import (
    InterfaceProvided,
    ModelInterfaceProvided,
)
from omnibase_core.models.ticket.model_requirement import (
    ModelRequirement,
    Requirement,
)
from omnibase_core.models.ticket.model_ticket_contract import (
    ModelTicketContract,
    TicketContract,
)
from omnibase_core.models.ticket.model_verification_step import (
    ModelVerificationStep,
    VerificationStep,
)

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
    # Sub-models (canonical names)
    "ModelClarifyingQuestion",
    "ModelInterfaceConsumed",
    "ModelInterfaceProvided",
    "ModelRequirement",
    "ModelVerificationStep",
    "ModelGate",
    # Aliases for cleaner API
    "ClarifyingQuestion",
    "InterfaceConsumed",
    "InterfaceProvided",
    "Requirement",
    "VerificationStep",
    "Gate",
    # Main contract (canonical name)
    "ModelTicketContract",
    # Alias for cleaner API
    "TicketContract",
    # Constants
    "PHASE_ALLOWED_ACTIONS",
]
