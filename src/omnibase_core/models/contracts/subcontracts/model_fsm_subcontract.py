"""
FSM (Finite State Machine) Subcontract Model.

Schema version: v1.5.0

Dedicated subcontract model for finite state machine functionality providing:
- State definitions with entry/exit actions and validation rules
- Transition specifications with conditions, actions, and rollback
- Operation definitions with permissions and atomic guarantees
- FSM configuration and management settings
- State lifecycle and transition validation
- Thread-safe immutability via frozen=True

This model is composed into node contracts that require FSM functionality,
providing clean separation between node logic and state machine behavior.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm.model_fsm_operation import ModelFSMOperation
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_fsm_state_definition import ModelFSMStateDefinition
from .model_fsm_state_transition import ModelFSMStateTransition


class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    Comprehensive state machine subcontract providing state definitions,
    transitions, operations, validation, and recovery mechanisms.
    Designed for composition into node contracts requiring FSM functionality.

    Schema Version:
        v1.5.0 - Added frozen=True for immutability after creation.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees:
        once an instance is created and validated, its state cannot be
        modified, allowing safe sharing across threads without locks.

        Model validators (validate_initial_state_exists, etc.) run during
        construction before the instance is frozen. After validation
        completes, the instance becomes immutable.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=5, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core FSM identification
    state_machine_name: str = Field(
        default=...,
        description="Unique name for the state machine",
        min_length=1,
    )

    state_machine_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the state machine definition (MUST be provided in YAML contract)",
    )

    description: str = Field(
        default=...,
        description="Human-readable state machine description",
        min_length=1,
    )

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for FSM instance tracking",
    )

    # State definitions
    states: list[ModelFSMStateDefinition] = Field(
        default=...,
        description="All available states in the system",
        min_length=1,
    )

    initial_state: str = Field(
        default=...,
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
        default=...,
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
        default=TIMEOUT_DEFAULT_MS,
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

    @model_validator(mode="after")
    def validate_initial_state_exists(self) -> "ModelFSMSubcontract":
        """Validate that initial state is defined in states list.

        Runs during construction before the instance is frozen. Ensures the
        initial_state field references a valid state from the states list.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If initial_state is not found in states list.
        """
        state_names = [state.state_name for state in self.states]
        if self.initial_state not in state_names:
            msg = f"Initial state '{self.initial_state}' not found in states list[Any]"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_special_states_exist(self) -> "ModelFSMSubcontract":
        """Validate that terminal and error states are defined in states list.

        Runs during construction before the instance is frozen. Ensures all
        states listed in terminal_states and error_states reference valid
        states from the states list.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If any terminal or error state is not found in
                states list.
        """
        state_names = [state.state_name for state in self.states]

        # Validate terminal states
        for state_name in self.terminal_states:
            if state_name not in state_names:
                msg = f"Terminal state '{state_name}' not found in states list[Any]"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )

        # Validate error states
        for state_name in self.error_states:
            if state_name not in state_names:
                msg = f"Error state '{state_name}' not found in states list[Any]"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_transition_states_exist(self) -> "ModelFSMSubcontract":
        """Validate that all transition source and target states exist.

        Runs during construction before the instance is frozen. Ensures all
        from_state and to_state values in transitions reference valid states.
        Supports wildcard transitions where from_state can be '*' to match
        any source state.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If any transition references a non-existent state.
        """
        state_names = [state.state_name for state in self.states]
        # Add wildcard state to supported states for global transitions
        state_names_with_wildcard = [*state_names, "*"]

        for transition in self.transitions:
            # Support wildcard transitions (from_state: '*')
            if transition.from_state not in state_names_with_wildcard:
                msg = f"Transition from_state '{transition.from_state}' not found in states list[Any]"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
            if transition.to_state not in state_names:
                msg = f"Transition to_state '{transition.to_state}' not found in states list[Any]"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_unique_transition_names(self) -> "ModelFSMSubcontract":
        """Validate that all transition names are unique.

        Runs during construction before the instance is frozen.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If duplicate transition names are found.
        """
        seen_names: set[str] = set()
        duplicates: set[str] = set()

        for transition in self.transitions:
            if transition.transition_name in seen_names:
                duplicates.add(transition.transition_name)
            seen_names.add(transition.transition_name)

        if duplicates:
            msg = f"Duplicate transition names found: {sorted(duplicates)}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_unique_structural_transitions(self) -> "ModelFSMSubcontract":
        """Validate that no duplicate structural transitions exist.

        Two transitions with identical (from_state, trigger, priority) tuple
        create ambiguous selection that definition order cannot reliably resolve.

        Runs during construction before the instance is frozen.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If duplicate structural transitions are found.
        """
        seen_tuples: set[tuple[str, str, int]] = set()
        duplicates: list[tuple[str, str, int]] = []

        for transition in self.transitions:
            key = (transition.from_state, transition.trigger, transition.priority)
            if key in seen_tuples:
                duplicates.append(key)
            seen_tuples.add(key)

        if duplicates:
            duplicate_strs = [
                f"(from_state='{fs}', trigger='{t}', priority={p})"
                for fs, t, p in duplicates
            ]
            msg = f"Duplicate structural transitions found: {duplicate_strs}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_no_transitions_from_terminal_states(self) -> "ModelFSMSubcontract":
        """Validate that terminal states have no outgoing transitions.

        Terminal states represent completed workflows that cannot be re-entered.
        Defining transitions from terminal states is a contract error.

        Runs during construction before the instance is frozen.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If transitions from terminal states are found.
        """
        # Get all terminal state names
        terminal_state_names: set[str] = set()
        for state in self.states:
            if state.is_terminal:
                terminal_state_names.add(state.state_name)

        # Also include explicitly declared terminal states
        terminal_state_names.update(self.terminal_states)

        # Check for transitions from terminal states (excluding wildcards)
        violations: list[str] = []
        for transition in self.transitions:
            if (
                transition.from_state in terminal_state_names
                and transition.from_state != "*"
            ):
                violations.append(
                    f"Transition '{transition.transition_name}' from terminal state "
                    f"'{transition.from_state}'"
                )

        if violations:
            msg = f"Transitions from terminal states are not allowed: {violations}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        from_attributes=True,  # Required for pytest-xdist compatibility
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
    )
