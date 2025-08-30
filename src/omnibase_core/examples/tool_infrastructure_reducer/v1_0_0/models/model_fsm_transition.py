"""
ModelFSMTransition - State transition definition with guards, actions, and rollback support.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides transition specification including conditions, effects, and recovery mechanisms.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelFSMTransition(BaseModel):
    """
    State transition definition with guards, actions, and rollback support.

    Defines transitions between states including:
    - Source and target state specification
    - Trigger events and conditions
    - Actions to execute during transition
    - Rollback and retry configuration
    """

    # Core identification
    transition_name: str = Field(
        ...,
        description="Unique identifier for the transition",
        pattern=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50,
    )

    # State transition specification
    from_state: str = Field(
        ...,
        description="Source state name (use '*' for any state)",
        pattern=r"^([a-z][a-z0-9_]*|\*)$",
    )

    to_state: str = Field(
        ..., description="Target state name", pattern=r"^[a-z][a-z0-9_]*$"
    )

    trigger: str = Field(
        ...,
        description="Event that triggers this transition",
        pattern=r"^ev_[a-z][a-z0-9_]*$",
    )

    priority: int = Field(
        default=1,
        description="Priority for conflict resolution (higher = higher priority)",
        ge=1,
        le=10,
    )

    # Transition logic
    conditions: List["ModelFSMGuard"] = Field(
        default_factory=list,
        description="Guard conditions that must be true for transition",
    )

    actions: List["ModelFSMEffect"] = Field(
        default_factory=list, description="Actions to execute during transition"
    )

    # Recovery configuration
    rollback_transitions: List[str] = Field(
        default_factory=list, description="Transitions to execute for rollback"
    )

    is_atomic: bool = Field(
        default=True, description="Whether this transition must complete atomically"
    )

    retry_enabled: bool = Field(
        default=False, description="Whether this transition supports retry on failure"
    )

    max_retries: Optional[int] = Field(
        default=None, description="Maximum number of retry attempts", ge=1, le=10
    )

    retry_delay_ms: Optional[int] = Field(
        default=None,
        description="Delay between retry attempts in milliseconds",
        ge=100,
        le=30000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transition_name": "bootstrap_to_loading",
                "from_state": "idle",
                "to_state": "loading_adapters",
                "trigger": "ev_bootstrap",
                "priority": 1,
                "conditions": [],
                "actions": [
                    {
                        "action_name": "log_bootstrap",
                        "action_type": "log",
                        "execution_order": 1,
                        "is_critical": False,
                    }
                ],
                "rollback_transitions": [],
                "is_atomic": True,
                "retry_enabled": False,
            }
        }


from .model_fsm_effect import ModelFSMEffect
# Import forward references after model definition
from .model_fsm_guard import ModelFSMGuard

# Update forward references
ModelFSMTransition.model_rebuild()
