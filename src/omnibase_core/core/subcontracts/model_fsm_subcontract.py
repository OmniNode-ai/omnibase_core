#!/usr/bin/env python3
"""
FSM (Finite State Machine) Subcontract Model - ONEX Standards Compliant.

Dedicated subcontract model for finite state machine functionality providing:
- State definitions with entry/exit actions and validation rules
- Transition specifications with conditions, actions, and rollback
- Operation definitions with permissions and atomic guarantees
- FSM configuration and management settings
- State lifecycle and transition validation

This model is composed into node contracts that require FSM functionality,
providing clean separation between node logic and state machine behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ModelFSMStateDefinition(BaseModel):
    """
    State definition for FSM subcontract.

    Defines state properties, lifecycle management,
    and validation rules for FSM state handling.
    """

    state_name: str = Field(..., description="Unique name for the state", min_length=1)

    state_type: str = Field(
        ...,
        description="Type classification (operational, snapshot, error, terminal)",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable state description",
        min_length=1,
    )

    is_terminal: bool = Field(
        default=False,
        description="Whether this is a terminal/final state",
    )

    is_recoverable: bool = Field(
        default=True,
        description="Whether recovery is possible from this state",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Maximum time allowed in this state",
        ge=1,
    )

    entry_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state entry",
    )

    exit_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state exit",
    )

    required_data: list[str] = Field(
        default_factory=list,
        description="Required data fields for this state",
    )

    optional_data: list[str] = Field(
        default_factory=list,
        description="Optional data fields for this state",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rules for state data",
    )


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.
    """

    condition_name: str = Field(
        ...,
        description="Unique name for the condition",
        min_length=1,
    )

    condition_type: str = Field(
        ...,
        description="Type of condition (validation, state, processing, custom)",
        min_length=1,
    )

    expression: str = Field(
        ...,
        description="Condition expression or rule",
        min_length=1,
    )

    required: bool = Field(
        default=True,
        description="Whether this condition is required for transition",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if condition fails",
    )

    retry_count: int = Field(
        default=0,
        description="Number of retries for failed conditions",
        ge=0,
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for condition evaluation",
        ge=1,
    )


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    action_name: str = Field(
        ...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        ...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict,
        description="Configuration parameters for the action",
    )

    execution_order: int = Field(
        default=1,
        description="Order of execution relative to other actions",
        ge=1,
    )

    is_critical: bool = Field(
        default=False,
        description="Whether action failure should abort transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Action to execute if rollback is needed",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for action execution",
        ge=1,
    )


class ModelFSMStateTransition(BaseModel):
    """
    State transition specification for FSM subcontract.

    Defines complete transition behavior including source/target states,
    triggers, conditions, actions, and rollback mechanisms.
    """

    transition_name: str = Field(
        ...,
        description="Unique name for the transition",
        min_length=1,
    )

    from_state: str = Field(..., description="Source state name", min_length=1)

    to_state: str = Field(..., description="Target state name", min_length=1)

    trigger: str = Field(
        ...,
        description="Event or condition that triggers transition",
        min_length=1,
    )

    priority: int = Field(
        default=1,
        description="Priority for conflict resolution",
        ge=1,
    )

    conditions: list[ModelFSMTransitionCondition] = Field(
        default_factory=list,
        description="Conditions that must be met for transition",
    )

    actions: list[ModelFSMTransitionAction] = Field(
        default_factory=list,
        description="Actions to execute during transition",
    )

    rollback_transitions: list[str] = Field(
        default_factory=list,
        description="Available rollback transition names",
    )

    is_atomic: bool = Field(
        default=True,
        description="Whether transition must complete atomically",
    )

    retry_enabled: bool = Field(
        default=False,
        description="Whether failed transitions can be retried",
    )

    max_retries: int = Field(
        default=0,
        description="Maximum number of retry attempts",
        ge=0,
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retry attempts",
        ge=0,
    )


class ModelFSMOperation(BaseModel):
    """
    Operation specification for FSM subcontract.

    Defines available operations for state transitions,
    constraints, and atomic operation guarantees.
    """

    operation_name: str = Field(
        ...,
        description="Unique name for the operation",
        min_length=1,
    )

    operation_type: str = Field(
        ...,
        description="Type of operation (create, update, delete, transition, snapshot, restore)",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable operation description",
        min_length=1,
    )

    requires_atomic_execution: bool = Field(
        default=True,
        description="Whether operation requires atomic execution",
    )

    supports_rollback: bool = Field(
        default=True,
        description="Whether operation supports rollback",
    )

    allowed_from_states: list[str] = Field(
        default_factory=list,
        description="States from which operation is allowed",
    )

    blocked_from_states: list[str] = Field(
        default_factory=list,
        description="States from which operation is blocked",
    )

    required_permissions: list[str] = Field(
        default_factory=list,
        description="Required permissions for operation",
    )

    side_effects: list[str] = Field(
        default_factory=list,
        description="Known side effects of the operation",
    )

    performance_impact: str = Field(
        default="low",
        description="Performance impact level (low, medium, high)",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Maximum execution time for operation",
        ge=1,
    )


class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    Comprehensive state machine subcontract providing state definitions,
    transitions, operations, validation, and recovery mechanisms.
    Designed for composition into node contracts requiring FSM functionality.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core FSM identification
    state_machine_name: str = Field(
        ...,
        description="Unique name for the state machine",
        min_length=1,
    )

    state_machine_version: str = Field(
        ...,
        description="Version of the state machine definition",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable state machine description",
        min_length=1,
    )

    # State definitions
    states: list[ModelFSMStateDefinition] = Field(
        ...,
        description="All available states in the system",
        min_length=1,
    )

    initial_state: str = Field(
        ...,
        description="Name of the initial state",
        min_length=1,
    )

    terminal_states: list[str] = Field(
        default_factory=list,
        description="Names of terminal/final states",
    )

    error_states: list[str] = Field(
        default_factory=list,
        description="Names of error/failure states",
    )

    # Transition specifications
    transitions: list[ModelFSMStateTransition] = Field(
        ...,
        description="All valid state transitions",
        min_length=1,
    )

    # Operation definitions
    operations: list[ModelFSMOperation] = Field(
        default_factory=list,
        description="Available transition operations",
    )

    # FSM persistence and recovery
    persistence_enabled: bool = Field(
        default=True,
        description="Whether state persistence is enabled",
    )

    checkpoint_interval_ms: int = Field(
        default=30000,
        description="Interval for automatic checkpoints",
        ge=1000,
    )

    max_checkpoints: int = Field(
        default=10,
        description="Maximum number of checkpoints to retain",
        ge=1,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Whether automatic recovery is enabled",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Whether rollback operations are enabled",
    )

    # Conflict resolution
    conflict_resolution_strategy: str = Field(
        default="priority_based",
        description="Strategy for resolving transition conflicts",
    )

    concurrent_transitions_allowed: bool = Field(
        default=False,
        description="Whether concurrent transitions are allowed",
    )

    transition_timeout_ms: int = Field(
        default=5000,
        description="Default timeout for transitions",
        ge=1,
    )

    # Validation and monitoring
    strict_validation_enabled: bool = Field(
        default=True,
        description="Whether strict state validation is enabled",
    )

    state_monitoring_enabled: bool = Field(
        default=True,
        description="Whether state monitoring/metrics are enabled",
    )

    event_logging_enabled: bool = Field(
        default=True,
        description="Whether state transition events are logged",
    )

    @field_validator("states")
    @classmethod
    def validate_initial_state_exists(
        cls,
        v: list[ModelFSMStateDefinition],
        info: ValidationInfo,
    ) -> list[ModelFSMStateDefinition]:
        """Validate that initial state is defined in states list."""
        if info.data and "initial_state" in info.data:
            state_names = [state.state_name for state in v]
            if info.data["initial_state"] not in state_names:
                msg = f"Initial state '{info.data['initial_state']}' not found in states list"
                raise ValueError(
                    msg,
                )
        return v

    @field_validator("terminal_states", "error_states")
    @classmethod
    def validate_special_states_exist(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Validate that terminal and error states are defined in states list."""
        if info.data and "states" in info.data and v:
            state_names = [state.state_name for state in info.data["states"]]
            for state_name in v:
                if state_name not in state_names:
                    msg = f"State '{state_name}' not found in states list"
                    raise ValueError(msg)
        return v

    @field_validator("transitions")
    @classmethod
    def validate_transition_states_exist(
        cls,
        v: list[ModelFSMStateTransition],
        info: ValidationInfo,
    ) -> list[ModelFSMStateTransition]:
        """Validate that all transition source and target states exist."""
        if info.data and "states" in info.data:
            state_names = [state.state_name for state in info.data["states"]]
            # Add wildcard state to supported states for global transitions
            state_names_with_wildcard = [*state_names, "*"]

            for transition in v:
                # Support wildcard transitions (from_state: '*')
                if transition.from_state not in state_names_with_wildcard:
                    msg = f"Transition from_state '{transition.from_state}' not found in states list"
                    raise ValueError(
                        msg,
                    )
                if transition.to_state not in state_names:
                    msg = f"Transition to_state '{transition.to_state}' not found in states list"
                    raise ValueError(
                        msg,
                    )
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
