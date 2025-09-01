"""
ModelFSMState - Individual state definition with metadata and validation rules.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides complete state specification including actions, data requirements, and validation.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FSMStateType(str, Enum):
    """Type classification of FSM states."""

    OPERATIONAL = "operational"
    ERROR = "error"
    TERMINAL = "terminal"
    TRANSITION = "transition"


class ModelFSMState(BaseModel):
    """
    Individual state definition with metadata and validation rules.

    Defines a single state within the finite state machine including:
    - State identification and classification
    - Entry and exit actions
    - Data requirements and validation rules
    - Timeout and recovery configuration
    """

    # Core identification
    state_name: str = Field(
        ...,
        description="Unique identifier for the state",
        pattern=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50,
    )

    state_type: FSMStateType = Field(
        ..., description="Type classification of the state"
    )

    description: str = Field(
        ...,
        description="Human-readable description of the state",
        min_length=5,
        max_length=200,
    )

    # State behavior
    is_terminal: bool = Field(..., description="Whether this state ends FSM execution")

    is_recoverable: bool = Field(
        ..., description="Whether this state supports recovery operations"
    )

    timeout_ms: Optional[int] = Field(
        default=None,
        description="Maximum time to spend in this state (milliseconds)",
        ge=100,
        le=300000,
    )

    # State actions
    entry_actions: List[str] = Field(
        default_factory=list, description="Actions to execute when entering this state"
    )

    exit_actions: List[str] = Field(
        default_factory=list, description="Actions to execute when exiting this state"
    )

    # Data requirements
    required_data: List[str] = Field(
        default_factory=list,
        description="Data fields required to be present in this state",
    )

    optional_data: List[str] = Field(
        default_factory=list,
        description="Data fields that may be present in this state",
    )

    validation_rules: List[str] = Field(
        default_factory=list, description="Validation rules to apply in this state"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state_name": "idle",
                "state_type": "operational",
                "description": "Initial idle state before bootstrap",
                "is_terminal": False,
                "is_recoverable": True,
                "entry_actions": ["log_entry"],
                "exit_actions": ["log_exit"],
                "required_data": [],
                "optional_data": ["correlation_id"],
                "validation_rules": [],
            }
        }
