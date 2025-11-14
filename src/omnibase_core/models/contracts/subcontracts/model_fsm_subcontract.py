"""
FSM (Finite State Machine) Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

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

import uuid
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_fsm_operation import ModelFSMOperation
from .model_fsm_state_definition import ModelFSMStateDefinition
from .model_fsm_state_transition import ModelFSMStateTransition


class ModelFSMSubcontract(BaseModel):
    """
    FSM (Finite State Machine) subcontract model.

    Comprehensive state machine subcontract providing state definitions,
    transitions, operations, validation, and recovery mechanisms.
    Designed for composition into node contracts requiring FSM functionality.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Core FSM identification
    state_machine_name: str = Field(
        default=...,
        description="Unique name for the state machine",
        min_length=1,
    )

    state_machine_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the state machine definition",
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

    @model_validator(mode="after")
    def validate_initial_state_exists(self) -> "ModelFSMSubcontract":
        """Validate that initial state is defined in states list[Any]."""
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
        """Validate that terminal and error states are defined in states list[Any]."""
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
        """Validate that all transition source and target states exist."""
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

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
