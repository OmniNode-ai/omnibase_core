from typing import Any

from pydantic import Field

"""
FSM State Transition Model - ONEX Standards Compliant.

Individual model for FSM state transition specification.
Part of the FSM Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel

from .model_fsm_transition_action import ModelFSMTransitionAction
from .model_fsm_transition_condition import ModelFSMTransitionCondition


class ModelFSMStateTransition(BaseModel):
    """
    State transition specification for FSM subcontract.

    Defines complete transition behavior including source/target states,
    triggers, conditions, actions, and rollback mechanisms.
    """

    transition_name: str = Field(
        default=...,
        description="Unique name for the transition",
        min_length=1,
    )

    from_state: str = Field(default=..., description="Source state name", min_length=1)

    to_state: str = Field(default=..., description="Target state name", min_length=1)

    trigger: str = Field(
        default=...,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
