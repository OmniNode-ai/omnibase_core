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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from omnibase_core.models.ticket.model_acceptance_criterion import (
        ModelAcceptanceCriterion,
    )
    from omnibase_core.models.ticket.model_clarifying_question import (
        ClarifyingQuestion,
        ModelClarifyingQuestion,
    )
    from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
    from omnibase_core.models.ticket.model_emergency_bypass import ModelEmergencyBypass
    from omnibase_core.models.ticket.model_evidence_requirement import (
        ModelEvidenceRequirement,
    )
    from omnibase_core.models.ticket.model_gate import (
        Gate,
        ModelGate,
    )
    from omnibase_core.models.ticket.model_golden_path import ModelGoldenPath
    from omnibase_core.models.ticket.model_golden_path_assertion import (
        ModelGoldenPathAssertion,
    )
    from omnibase_core.models.ticket.model_golden_path_input import ModelGoldenPathInput
    from omnibase_core.models.ticket.model_golden_path_output import (
        ModelGoldenPathOutput,
    )
    from omnibase_core.models.ticket.model_interface_consumed import (
        InterfaceConsumed,
        ModelInterfaceConsumed,
    )
    from omnibase_core.models.ticket.model_interface_provided import (
        InterfaceProvided,
        ModelInterfaceProvided,
    )
    from omnibase_core.models.ticket.model_proof_requirement import (
        ModelProofRequirement,
    )
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
    from omnibase_core.models.ticket.model_ticket_workflow_state import (
        ModelTicketWorkflowState,
    )
    from omnibase_core.models.ticket.model_verification_step import (
        ModelVerificationStep,
        VerificationStep,
    )
    from omnibase_core.models.ticket.model_workflow_context import ModelWorkflowContext
    from omnibase_core.models.ticket.model_workflow_gate import ModelWorkflowGate
    from omnibase_core.models.ticket.model_workflow_question import (
        ModelWorkflowQuestion,
    )
    from omnibase_core.models.ticket.model_workflow_requirement import (
        ModelWorkflowRequirement,
    )
    from omnibase_core.models.ticket.model_workflow_verification import (
        ModelWorkflowVerification,
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
    # OMN-10064: OCC-origin merged models
    "ModelContractDodItem",
    "ModelEmergencyBypass",
    "ModelEvidenceRequirement",
    "ModelGoldenPath",
    "ModelGoldenPathAssertion",
    "ModelGoldenPathInput",
    "ModelGoldenPathOutput",
    # Workflow state (distinct from ModelTicketContract) — FSM state embedded
    # in Linear ticket descriptions by the ticket-work handler.
    "ModelTicketWorkflowState",
    "ModelWorkflowContext",
    "ModelWorkflowGate",
    "ModelWorkflowQuestion",
    "ModelWorkflowRequirement",
    "ModelWorkflowVerification",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "PHASE_ALLOWED_ACTIONS": ("omnibase_core.enums.ticket", "PHASE_ALLOWED_ACTIONS"),
    "Action": ("omnibase_core.enums.ticket", "Action"),
    "EnumGateKind": ("omnibase_core.enums.ticket", "EnumGateKind"),
    "EnumTicketAction": ("omnibase_core.enums.ticket", "EnumTicketAction"),
    "EnumTicketPhase": ("omnibase_core.enums.ticket", "EnumTicketPhase"),
    "EnumTicketStepStatus": ("omnibase_core.enums.ticket", "EnumTicketStepStatus"),
    "EnumVerificationKind": ("omnibase_core.enums.ticket", "EnumVerificationKind"),
    "GateKind": ("omnibase_core.enums.ticket", "GateKind"),
    "Phase": ("omnibase_core.enums.ticket", "Phase"),
    "Status": ("omnibase_core.enums.ticket", "Status"),
    "VerificationKind": ("omnibase_core.enums.ticket", "VerificationKind"),
    "ModelAcceptanceCriterion": (
        "omnibase_core.models.ticket.model_acceptance_criterion",
        "ModelAcceptanceCriterion",
    ),
    "ClarifyingQuestion": (
        "omnibase_core.models.ticket.model_clarifying_question",
        "ClarifyingQuestion",
    ),
    "ModelClarifyingQuestion": (
        "omnibase_core.models.ticket.model_clarifying_question",
        "ModelClarifyingQuestion",
    ),
    "ModelContractDodItem": (
        "omnibase_core.models.ticket.model_contract_dod_item",
        "ModelContractDodItem",
    ),
    "ModelEmergencyBypass": (
        "omnibase_core.models.ticket.model_emergency_bypass",
        "ModelEmergencyBypass",
    ),
    "ModelEvidenceRequirement": (
        "omnibase_core.models.ticket.model_evidence_requirement",
        "ModelEvidenceRequirement",
    ),
    "Gate": ("omnibase_core.models.ticket.model_gate", "Gate"),
    "ModelGate": ("omnibase_core.models.ticket.model_gate", "ModelGate"),
    "ModelGoldenPath": (
        "omnibase_core.models.ticket.model_golden_path",
        "ModelGoldenPath",
    ),
    "ModelGoldenPathAssertion": (
        "omnibase_core.models.ticket.model_golden_path_assertion",
        "ModelGoldenPathAssertion",
    ),
    "ModelGoldenPathInput": (
        "omnibase_core.models.ticket.model_golden_path_input",
        "ModelGoldenPathInput",
    ),
    "ModelGoldenPathOutput": (
        "omnibase_core.models.ticket.model_golden_path_output",
        "ModelGoldenPathOutput",
    ),
    "InterfaceConsumed": (
        "omnibase_core.models.ticket.model_interface_consumed",
        "InterfaceConsumed",
    ),
    "ModelInterfaceConsumed": (
        "omnibase_core.models.ticket.model_interface_consumed",
        "ModelInterfaceConsumed",
    ),
    "InterfaceProvided": (
        "omnibase_core.models.ticket.model_interface_provided",
        "InterfaceProvided",
    ),
    "ModelInterfaceProvided": (
        "omnibase_core.models.ticket.model_interface_provided",
        "ModelInterfaceProvided",
    ),
    "ModelProofRequirement": (
        "omnibase_core.models.ticket.model_proof_requirement",
        "ModelProofRequirement",
    ),
    "ModelRequirement": (
        "omnibase_core.models.ticket.model_requirement",
        "ModelRequirement",
    ),
    "Requirement": ("omnibase_core.models.ticket.model_requirement", "Requirement"),
    "ModelTCBAssumption": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBAssumption",
    ),
    "ModelTCBConstraint": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBConstraint",
    ),
    "ModelTCBEntrypoint": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBEntrypoint",
    ),
    "ModelTCBIntent": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBIntent",
    ),
    "ModelTCBNormalizedIntent": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBNormalizedIntent",
    ),
    "ModelTCBPattern": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBPattern",
    ),
    "ModelTCBProvenance": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBProvenance",
    ),
    "ModelTCBRelatedChange": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBRelatedChange",
    ),
    "ModelTCBTestRecommendation": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTCBTestRecommendation",
    ),
    "ModelTicketContextBundle": (
        "omnibase_core.models.ticket.model_ticket_context_bundle",
        "ModelTicketContextBundle",
    ),
    "ModelTicketContract": (
        "omnibase_core.models.ticket.model_ticket_contract",
        "ModelTicketContract",
    ),
    "TicketContract": (
        "omnibase_core.models.ticket.model_ticket_contract",
        "TicketContract",
    ),
    "ModelTicketWorkflowState": (
        "omnibase_core.models.ticket.model_ticket_workflow_state",
        "ModelTicketWorkflowState",
    ),
    "ModelVerificationStep": (
        "omnibase_core.models.ticket.model_verification_step",
        "ModelVerificationStep",
    ),
    "VerificationStep": (
        "omnibase_core.models.ticket.model_verification_step",
        "VerificationStep",
    ),
    "ModelWorkflowContext": (
        "omnibase_core.models.ticket.model_workflow_context",
        "ModelWorkflowContext",
    ),
    "ModelWorkflowGate": (
        "omnibase_core.models.ticket.model_workflow_gate",
        "ModelWorkflowGate",
    ),
    "ModelWorkflowQuestion": (
        "omnibase_core.models.ticket.model_workflow_question",
        "ModelWorkflowQuestion",
    ),
    "ModelWorkflowRequirement": (
        "omnibase_core.models.ticket.model_workflow_requirement",
        "ModelWorkflowRequirement",
    ),
    "ModelWorkflowVerification": (
        "omnibase_core.models.ticket.model_workflow_verification",
        "ModelWorkflowVerification",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
