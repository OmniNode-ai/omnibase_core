"""
Strongly-typed FSM data structure model.

Replaces dict[str, Any] usage in FSM operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import Executable

from .model_fsm_state import ModelFsmState
from .model_fsm_transition import ModelFsmTransition


class ModelFsmData(BaseModel):
    """
    Strongly-typed FSM data structure.

    Replaces dict[str, Any] with structured FSM model.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    state_machine_name: str = Field(..., description="Name of the state machine")
    description: str = Field(default="", description="State machine description")
    initial_state: str = Field(..., description="Initial state name")
    states: list[ModelFsmState] = Field(..., description="List of states")
    transitions: list[ModelFsmTransition] = Field(
        ..., description="List of transitions"
    )
    variables: dict[str, str] = Field(
        default_factory=dict, description="State machine variables"
    )
    global_actions: list[str] = Field(
        default_factory=list, description="Global actions available"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def get_state_by_name(self, name: str) -> ModelFsmState | None:
        """Get a state by name."""
        for state in self.states:
            if state.name == name:
                return state
        return None

    def get_transitions_from_state(self, state_name: str) -> list[ModelFsmTransition]:
        """Get all transitions from a specific state."""
        return [t for t in self.transitions if t.from_state == state_name]

    def get_transitions_to_state(self, state_name: str) -> list[ModelFsmTransition]:
        """Get all transitions to a specific state."""
        return [t for t in self.transitions if t.to_state == state_name]

    def validate_fsm_structure(self) -> list[str]:
        """Validate FSM structure and return list of validation errors."""
        errors = []

        if not self.initial_state:
            errors.append("No initial state specified")

        state_names = {state.name for state in self.states}

        # Check if initial state exists
        if self.initial_state not in state_names:
            errors.append(f"Initial state '{self.initial_state}' not found in states")

        # Check transition validity
        for transition in self.transitions:
            if transition.from_state not in state_names:
                errors.append(f"Transition from unknown state: {transition.from_state}")
            if transition.to_state not in state_names:
                errors.append(f"Transition to unknown state: {transition.to_state}")

        # Check for at least one final state
        if not any(state.is_final for state in self.states):
            errors.append("No final states defined")

        return errors

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelFsmData"]
