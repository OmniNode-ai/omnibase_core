# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ticket contract and context bundle models.

Exports TicketContract (contract-driven ticket execution with phases, actions,
verification steps, and gates) and ModelTicketContextBundle (provenance-stamped,
TTL-bound context artifact for ticket work).

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
from omnibase_core.models.ticket.model_acceptance_criterion import (
    ModelAcceptanceCriterion,
)
from omnibase_core.models.ticket.model_proof_requirement import ModelProofRequirement
from omnibase_core.models.ticket.model_requirement import (
    ModelRequirement,
    Requirement,
)
from omnibase_core.models.ticket.model_ticket_context_bundle import (
    ModelTCBAssumption,
    ModelTCBConstraint,
    ModelTCBEntrypoint,
    ModelTCBIntent,
    ModelTCBNormalizedIntent,
    ModelTCBPattern,
    ModelTCBProvenance,
    ModelTCBRelatedChange,
    ModelTCBTestRecommendation,
    ModelTicketContextBundle,
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
    "ModelAcceptanceCriterion",
    "ModelClarifyingQuestion",
    "ModelInterfaceConsumed",
    "ModelInterfaceProvided",
    "ModelProofRequirement",
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
    # TCB models
    "ModelTicketContextBundle",
    "ModelTCBIntent",
    "ModelTCBNormalizedIntent",
    "ModelTCBEntrypoint",
    "ModelTCBRelatedChange",
    "ModelTCBPattern",
    "ModelTCBTestRecommendation",
    "ModelTCBConstraint",
    "ModelTCBAssumption",
    "ModelTCBProvenance",
]
