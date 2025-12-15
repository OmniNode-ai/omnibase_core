"""
FSM State Transition Model.

Schema version: v1.5.0

Individual model for FSM state transition specification.
Part of the FSM Subcontract Model family.

This model defines complete transition behavior including source/target states,
triggers, conditions, actions, and rollback mechanisms.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.fsm.model_fsm_transition_action import (
    ModelFSMTransitionAction,
)
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateTransition(BaseModel):
    """
    State transition specification for FSM subcontract.

    Defines complete transition behavior including source/target states,
    triggers, conditions, actions, and rollback mechanisms.

    Schema Version:
        v1.5.0 - Added frozen=True for immutability after creation.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees.

    Priority Resolution:
        - Higher priority wins (descending sort)
        - Within same priority, declaration order is the tiebreaker
        - Default priority is 0 (lowest)

    Wildcard Support:
        The from_state field supports "*" as a wildcard to match any source state,
        useful for global error handlers or catch-all transitions.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    transition_name: str = Field(
        default=...,
        description="Unique name for the transition",
        min_length=1,
    )

    from_state: str = Field(
        default=...,
        description="Source state name (or '*' for wildcard)",
        min_length=1,
    )

    to_state: str = Field(default=..., description="Target state name", min_length=1)

    trigger: str = Field(
        default=...,
        description="Event or condition that triggers transition",
        min_length=1,
    )

    priority: int = Field(
        default=0,
        description="Priority for conflict resolution (higher wins, default: 0)",
        ge=0,
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
        description="Available rollback transition names (reserved for v1.2+)",
    )

    is_atomic: bool = Field(
        default=True,
        description="Whether transition must complete atomically",
    )

    retry_enabled: bool = Field(
        default=False,
        description="Whether failed transitions can be retried (reserved for v1.1+)",
    )

    max_retries: int = Field(
        default=0,
        description="Maximum number of retry attempts (reserved for v1.1+)",
        ge=0,
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retry attempts in milliseconds (reserved for v1.1+)",
        ge=0,
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        from_attributes=True,  # Allow validation via attribute access for nested models
    )
