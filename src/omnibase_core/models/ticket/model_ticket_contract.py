"""TicketContract model for contract-driven ticket execution.

Provides the main contract model for the /ticket-work skill automation system.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.ticket import (
    PHASE_ALLOWED_ACTIONS,
    EnumTicketAction,
    EnumTicketPhase,
    EnumTicketStepStatus,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.ticket.model_clarifying_question import (
    ModelClarifyingQuestion,
)
from omnibase_core.models.ticket.model_gate import ModelGate
from omnibase_core.models.ticket.model_interface_consumed import (
    ModelInterfaceConsumed,
)
from omnibase_core.models.ticket.model_interface_provided import (
    ModelInterfaceProvided,
)
from omnibase_core.models.ticket.model_requirement import ModelRequirement
from omnibase_core.models.ticket.model_verification_step import ModelVerificationStep
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(reason="External Linear ticket identifier (e.g., OMN-1807)")
@allow_dict_str_any(
    reason="Context accumulates arbitrary research data during workflow"
)
class ModelTicketContract(BaseModel):
    """Contract model for ticket-driven development workflow.

    This model tracks the complete state of a ticket through its lifecycle,
    from intake through implementation and review. It enforces phase-based
    action restrictions and tracks verification and approval gates.

    Mutability:
        This model is mutable (NOT frozen) to allow state updates during
        workflow execution. Use update_fingerprint() after modifications.

    YAML Persistence:
        The contract is designed to be serialized to/from YAML for persistence.
        Use to_yaml() and from_yaml() methods for serialization.
    """

    # Ticket identification
    # string-id-ok: External Linear ticket identifier (e.g., OMN-1807)
    ticket_id: str = Field(..., description="External ticket ID (e.g., OMN-1807)")
    title: str = Field(..., description="Ticket title")
    description: str = Field(default="", description="Ticket description")

    # Workflow state
    phase: EnumTicketPhase = Field(
        default=EnumTicketPhase.INTAKE, description="Current workflow phase"
    )

    # Context and research
    # dict-str-any-ok: Context accumulates arbitrary research data during workflow
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Gathered context including code snippets, docs, etc.",
    )

    # Clarifying questions
    questions: list[ModelClarifyingQuestion] = Field(
        default_factory=list, description="Clarifying questions for requirements"
    )

    # Requirements specification
    requirements: list[ModelRequirement] = Field(
        default_factory=list, description="Requirements derived from ticket"
    )

    # Verification and gates
    verification_steps: list[ModelVerificationStep] = Field(
        default_factory=list, description="Verification steps to run"
    )
    gates: list[ModelGate] = Field(
        default_factory=list, description="Approval gates required"
    )

    # Interface contracts for parallel development
    interfaces_provided: list[ModelInterfaceProvided] = Field(
        default_factory=list,
        description="Interfaces this ticket provides to other tickets",
    )
    interfaces_consumed: list[ModelInterfaceConsumed] = Field(
        default_factory=list,
        description="Interfaces this ticket consumes (may be mocked)",
    )

    # Fingerprinting and timestamps
    contract_fingerprint: str | None = Field(
        default=None, description="SHA256 fingerprint of contract state"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the contract was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the contract was last updated (UTC)",
    )

    # Allow extra fields for extensibility (YAML contracts may have additional fields)
    model_config = ConfigDict(
        extra="allow",
        from_attributes=True,
    )

    # =========================================================================
    # research_notes as @property (derived from context)
    # =========================================================================

    @property
    def research_notes(self) -> str:
        """Derive research notes from context.

        This is a computed property that extracts research-related information
        from the context dict. It is NOT included in model_dump() output.

        Returns:
            Research notes as a string, or empty string if not present.
        """
        notes = self.context.get("research_notes", "")
        if isinstance(notes, str):
            return notes
        if isinstance(notes, list):
            return "\n".join(str(n) for n in notes)
        return str(notes) if notes else ""

    # =========================================================================
    # Phase Enforcement Methods
    # =========================================================================

    def allowed_actions(self) -> frozenset[EnumTicketAction]:
        """Get the frozenset of actions allowed in the current phase.

        Returns:
            Frozenset of EnumTicketAction enum values (not strings).
        """
        return PHASE_ALLOWED_ACTIONS.get(self.phase, frozenset())

    def assert_action_allowed(self, action: EnumTicketAction | str) -> None:
        """Assert that an action is allowed in the current phase.

        Accepts both enum values and strings for CLI ergonomics.

        Args:
            action: The action to check (enum or string).

        Raises:
            ModelOnexError: If the action is not allowed in the current phase.
        """
        # Normalize string input to enum
        if isinstance(action, str):
            try:
                action = EnumTicketAction(action)
            except ValueError as e:
                raise ModelOnexError(
                    message=f"Invalid action: {action!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    action=action,
                    valid_actions=[a.value for a in EnumTicketAction],
                ) from e

        allowed = self.allowed_actions()
        if action not in allowed:
            raise ModelOnexError(
                message=(
                    f"Action {action.value!r} is not allowed in phase {self.phase.value!r}. "
                    f"Allowed actions: {[a.value for a in allowed]}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                action=action.value,
                phase=self.phase.value,
                allowed_actions=[a.value for a in allowed],
            )

    # =========================================================================
    # Completion Check Methods
    # =========================================================================

    def is_questions_complete(self) -> bool:
        """Check if all required questions have non-empty answers."""
        for q in self.questions:
            if q.required and (not q.answer or not q.answer.strip()):
                return False
        return True

    def is_spec_complete(self) -> bool:
        """Check if specification is complete.

        Requires at least one requirement, and all requirements must have
        at least one acceptance criterion.
        """
        if not self.requirements:
            return False

        for req in self.requirements:
            if not req.acceptance:
                return False

        return True

    def is_verification_complete(self) -> bool:
        """Check if all blocking verification steps have passed or been skipped."""
        for step in self.verification_steps:
            if step.blocking:
                if step.status not in (
                    EnumTicketStepStatus.PASSED,
                    EnumTicketStepStatus.SKIPPED,
                ):
                    return False
        return True

    def is_gates_complete(self) -> bool:
        """Check if all required gates have been approved."""
        for gate in self.gates:
            if gate.required and gate.status != EnumTicketStepStatus.APPROVED:
                return False
        return True

    def is_done(self) -> bool:
        """Check if ticket is fully complete.

        Requires phase is DONE and all completion checks pass.
        """
        return (
            self.phase == EnumTicketPhase.DONE
            and self.is_questions_complete()
            and self.is_spec_complete()
            and self.is_verification_complete()
            and self.is_gates_complete()
        )

    def pending_questions(self) -> list[ModelClarifyingQuestion]:
        """Get questions that still need answers."""
        return [
            q
            for q in self.questions
            if q.required and (not q.answer or not q.answer.strip())
        ]

    def blocking_verification(self) -> list[ModelVerificationStep]:
        """Get blocking verification steps that haven't passed."""
        return [
            step
            for step in self.verification_steps
            if step.blocking
            and step.status
            not in (EnumTicketStepStatus.PASSED, EnumTicketStepStatus.SKIPPED)
        ]

    def pending_gates(self) -> list[ModelGate]:
        """Get gates that still need approval."""
        return [
            gate
            for gate in self.gates
            if gate.required and gate.status != EnumTicketStepStatus.APPROVED
        ]

    # =========================================================================
    # Fingerprinting Methods
    # =========================================================================

    def compute_fingerprint(self) -> str:
        """Compute a 16-character hex SHA256 fingerprint of the contract.

        The fingerprint excludes the contract_fingerprint field itself.
        """
        data = self.model_dump(exclude={"contract_fingerprint"})
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def update_fingerprint(self) -> None:
        """Update the contract fingerprint and updated_at timestamp."""
        self.contract_fingerprint = self.compute_fingerprint()
        self.updated_at = datetime.now(tz=UTC)

    def __repr__(self) -> str:
        """Return concise representation for debugging."""
        return (
            f"ModelTicketContract("
            f"id={self.ticket_id!r}, "
            f"phase={self.phase.value!r}, "
            f"questions={len(self.questions)}, "
            f"requirements={len(self.requirements)}, "
            f"verification={len(self.verification_steps)}, "
            f"gates={len(self.gates)})"
        )

    # =========================================================================
    # YAML Serialization
    # =========================================================================

    def to_yaml(self) -> str:
        """Serialize the contract to YAML.

        Uses mode='json' to ensure datetime and enum serialization.
        """
        data = self.model_dump(mode="json")
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ModelTicketContract:
        """Deserialize a contract from YAML.

        Args:
            yaml_str: YAML string to parse.

        Returns:
            ModelTicketContract instance.

        Raises:
            ModelOnexError: If YAML parsing or validation fails.
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"Failed to parse YAML: {e}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from e

        if not isinstance(data, dict):
            raise ModelOnexError(
                message=f"Expected dict from YAML, got {type(data).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise ModelOnexError(
                message=f"Contract validation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e


# Alias for cleaner imports
TicketContract = ModelTicketContract

__all__ = [
    "ModelTicketContract",
    "TicketContract",
]
