"""
Strongly-typed FSM data structure model.

Replaces dict[str, Any] usage in FSM operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

Deep Immutability:
    This model uses frozen=True for Pydantic immutability, but also uses
    immutable types (tuple instead of list, tuple-of-tuples instead of dict)
    for deep immutability. This ensures that nested collections cannot be
    modified after construction.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_validators import (
    convert_dict_to_frozen_pairs,
    convert_list_to_tuple,
)

from .model_fsm_state import ModelFsmState
from .model_fsm_transition import ModelFsmTransition


class ModelFsmData(BaseModel):
    """
    Strongly-typed FSM data structure with deep immutability.

    Replaces dict[str, Any] with structured FSM model.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Deep Immutability:
        All collection fields use immutable types:
        - states/transitions/global_actions: tuple instead of list
        - variables/metadata: tuple[tuple[str, str], ...] instead of dict

        Validators automatically convert incoming lists/dicts to frozen types
        for convenience during model construction.

    Accessing dict-like fields:
        For variables and metadata, use dict() to convert back:
        >>> fsm = ModelFsmData(...)
        >>> vars_dict = dict(fsm.variables)  # Convert to dict for lookup
        >>> meta_dict = dict(fsm.metadata)
    """

    state_machine_name: str = Field(
        default=..., description="Name of the state machine"
    )
    description: str = Field(default="", description="State machine description")
    initial_state: str = Field(default=..., description="Initial state name")
    states: tuple[ModelFsmState, ...] = Field(
        default=..., description="Tuple of states (immutable)"
    )
    transitions: tuple[ModelFsmTransition, ...] = Field(
        default=..., description="Tuple of transitions (immutable)"
    )
    variables: tuple[tuple[str, str], ...] = Field(
        default=(), description="State machine variables as frozen key-value pairs"
    )
    global_actions: tuple[str, ...] = Field(
        default=(), description="Global actions available (immutable)"
    )
    metadata: tuple[tuple[str, str], ...] = Field(
        default=(), description="Additional metadata as frozen key-value pairs"
    )

    # -------------------------------------------------------------------------
    # Type Ignore Pattern Explanation:
    # These validators use `# type: ignore[return-value]` because:
    # 1. Input type is `list[...] | tuple[...] | object` to accept various inputs
    # 2. When input is already a tuple, we return it directly
    # 3. Type checker can't verify `object` is actually `tuple[...]`
    # 4. This is safe because Pydantic validates the final field type
    # This pattern is used throughout FSM/workflow models for list-to-tuple conversion.
    # See PR #298 for context: replaced `Any` with `object` for stronger typing.
    # -------------------------------------------------------------------------

    @field_validator("states", mode="before")
    @classmethod
    def _convert_states_to_tuple(
        cls, v: list[object] | tuple[object, ...] | object
    ) -> tuple[object, ...]:
        """Convert list of states to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("transitions", mode="before")
    @classmethod
    def _convert_transitions_to_tuple(
        cls, v: list[object] | tuple[object, ...] | object
    ) -> tuple[object, ...]:
        """Convert list of transitions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("global_actions", mode="before")
    @classmethod
    def _convert_global_actions_to_tuple(
        cls, v: list[str] | tuple[str, ...] | object
    ) -> tuple[str, ...]:
        """Convert list of global actions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("variables", mode="before")
    @classmethod
    def _convert_variables_to_frozen(
        cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
    ) -> tuple[tuple[str, str], ...]:
        """Convert dict to tuple of tuples for deep immutability.

        Keys are sorted for deterministic ordering, which ensures consistent
        hashing and comparison of model instances.
        """
        return convert_dict_to_frozen_pairs(v, sort_keys=True)

    @field_validator("metadata", mode="before")
    @classmethod
    def _convert_metadata_to_frozen(
        cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
    ) -> tuple[tuple[str, str], ...]:
        """Convert dict to tuple of tuples for deep immutability.

        Keys are sorted for deterministic ordering, which ensures consistent
        hashing and comparison of model instances.
        """
        return convert_dict_to_frozen_pairs(v, sort_keys=True)

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Note: In v1.0, this method returns True without modification.
        The model is frozen (immutable) for thread safety.
        """
        # v1.0: Model is frozen, so setattr is not allowed
        _ = kwargs  # Explicitly mark as unused
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Validates that required fields have valid values:
        - state_machine_name must be a non-empty, non-whitespace string
        - initial_state must be a non-empty, non-whitespace string

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate state_machine_name is non-empty
        if not self.state_machine_name or not self.state_machine_name.strip():
            return False
        # Validate initial_state is non-empty
        if not self.initial_state or not self.initial_state.strip():
            return False
        return True


# Export for use
__all__ = ["ModelFsmData"]
