"""
ModelFSMDefinition - Complete finite state machine definition.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides comprehensive state machine structure with states, transitions, and operations.
"""

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationInfo, field_validator

if TYPE_CHECKING:
    from .model_fsm_operation import ModelFSMOperation
    from .model_fsm_state import ModelFSMState
    from .model_fsm_transition import ModelFSMTransition


class FSMConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicting state transitions."""

    PRIORITY_BASED = "priority_based"
    TIMESTAMP_BASED = "timestamp_based"
    STRICT_ORDER = "strict_order"


class ModelFSMDefinition(BaseModel):
    """
    Complete finite state machine definition with states, transitions, and operations.

    This model defines the complete structure of a finite state machine including:
    - State definitions with entry/exit actions
    - Transition definitions with guards and effects
    - Operation definitions with permissions and constraints
    - FSM configuration and management settings
    """

    # Core identification
    state_machine_name: str = Field(
        ...,
        description="Unique identifier for the state machine",
        pattern=r"^[A-Za-z][A-Za-z0-9_]*FSM$",
        min_length=4,
        max_length=100,
    )

    state_machine_version: str = Field(
        ...,
        description="Semantic version of the state machine",
        pattern=r"^\d+\.\d+\.\d+$",
    )

    description: str = Field(
        ...,
        description="Human-readable description of the state machine purpose",
        min_length=10,
        max_length=500,
    )

    # State machine structure
    initial_state: str = Field(
        ...,
        description="Name of the initial state when FSM starts",
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    terminal_states: list[str] = Field(
        default_factory=list,
        description="List of terminal states that end FSM execution",
    )

    error_states: list[str] = Field(
        default_factory=list,
        description="List of error states for error handling",
    )

    # FSM components
    states: list["ModelFSMState"] = Field(
        ...,
        description="Complete list of state definitions",
        min_items=1,
    )

    transitions: list["ModelFSMTransition"] = Field(
        ...,
        description="Complete list of transition definitions",
        min_items=1,
    )

    operations: list["ModelFSMOperation"] = Field(
        default_factory=list,
        description="Available operations within the FSM",
    )

    # FSM Configuration
    persistence_enabled: bool = Field(
        default=True,
        description="Whether FSM state should be persisted",
    )

    checkpoint_interval_ms: int = Field(
        default=30000,
        description="Interval for state checkpoints in milliseconds",
        ge=1000,
        le=300000,
    )

    max_checkpoints: int = Field(
        default=10,
        description="Maximum number of checkpoints to retain",
        ge=1,
        le=100,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Whether FSM supports recovery from failures",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Whether FSM supports transaction rollback",
    )

    conflict_resolution_strategy: FSMConflictResolutionStrategy = Field(
        default=FSMConflictResolutionStrategy.PRIORITY_BASED,
        description="Strategy for resolving conflicting state transitions",
    )

    concurrent_transitions_allowed: bool = Field(
        default=False,
        description="Whether multiple transitions can occur simultaneously",
    )

    transition_timeout_ms: int = Field(
        default=5000,
        description="Default timeout for transitions in milliseconds",
        ge=100,
        le=60000,
    )

    strict_validation_enabled: bool = Field(
        default=True,
        description="Whether to enforce strict validation of all FSM components",
    )

    state_monitoring_enabled: bool = Field(
        default=True,
        description="Whether to enable state monitoring and metrics",
    )

    event_logging_enabled: bool = Field(
        default=True,
        description="Whether to log all FSM events",
    )

    @field_validator("states")
    @classmethod
    def validate_states_contain_initial(cls, v, info: ValidationInfo):
        """Validate that states list contains the initial state."""
        if "initial_state" in info.data:
            initial_state = info.data["initial_state"]
            state_names = [state.state_name for state in v]
            if initial_state not in state_names:
                msg = f"Initial state '{initial_state}' not found in states list"
                raise ValueError(
                    msg,
                )
        return v

    @field_validator("terminal_states", "error_states")
    @classmethod
    def validate_special_states_exist(cls, v, info: ValidationInfo):
        """Validate that terminal and error states exist in the states list."""
        if "states" in info.data and v:
            state_names = [state.state_name for state in info.data["states"]]
            for state_name in v:
                if state_name not in state_names:
                    msg = f"State '{state_name}' not found in states list"
                    raise ValueError(msg)
        return v

    @field_validator("transitions")
    @classmethod
    def validate_transition_states_exist(cls, v, info: ValidationInfo):
        """Validate that all transition from/to states exist."""
        if "states" in info.data:
            state_names = {state.state_name for state in info.data["states"]}
            for transition in v:
                # Handle wildcard 'from_state'
                if (
                    transition.from_state != "*"
                    and transition.from_state not in state_names
                ):
                    msg = f"Transition from_state '{transition.from_state}' not found in states"
                    raise ValueError(
                        msg,
                    )
                if transition.to_state not in state_names:
                    msg = f"Transition to_state '{transition.to_state}' not found in states"
                    raise ValueError(
                        msg,
                    )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "state_machine_name": "InfrastructureReducerFSM",
                "state_machine_version": "1.0.0",
                "description": "State machine for infrastructure service with adapter loading and health monitoring",
                "initial_state": "idle",
                "terminal_states": ["disabled"],
                "error_states": ["error"],
                "persistence_enabled": True,
                "recovery_enabled": True,
                "conflict_resolution_strategy": "priority_based",
            },
        }


# Forward references will be resolved automatically by Pydantic v2 when models are used
# Removed model_rebuild() call that was causing circular import issues
