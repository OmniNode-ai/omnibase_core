"""
ModelFSMEffect - Side effect or action to execute during state transition.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides action specification including configuration, timing, and recovery options.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FSMActionType(str, Enum):
    """Type of actions that can be executed during transitions."""

    LOG = "log"
    EVENT = "event"
    MODIFY = "modify"
    VALIDATE = "validate"
    CLEANUP = "cleanup"
    NOTIFY = "notify"
    CUSTOM = "custom"


class ModelFSMEffect(BaseModel):
    """
    Side effect or action to execute during state transition.

    Defines actions that execute as part of state transitions including:
    - Action identification and classification
    - Configuration parameters for execution
    - Execution order and criticality
    - Retry and rollback configuration
    """

    # Core identification
    action_name: str = Field(
        ...,
        description="Unique identifier for the action",
        pattern=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50,
    )

    action_type: FSMActionType = Field(..., description="Type of action to execute")

    action_config: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters for the action"
    )

    # Execution configuration
    execution_order: int = Field(
        ...,
        description="Order of execution within transition (lower = earlier)",
        ge=1,
        le=100,
    )

    is_critical: bool = Field(
        ..., description="Whether failure of this action should abort transition"
    )

    timeout_ms: int = Field(
        default=1000,
        description="Timeout for action execution in milliseconds",
        ge=10,
        le=30000,
    )

    # Recovery configuration
    retry_on_failure: bool = Field(
        default=False, description="Whether to retry this action on failure"
    )

    max_retries: Optional[int] = Field(
        default=None, description="Maximum retry attempts for this action", ge=1, le=5
    )

    rollback_action: Optional[str] = Field(
        default=None,
        description="Action to execute for rollback",
        pattern=r"^[a-z][a-z0-9_]*$",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "action_name": "log_bootstrap",
                "action_type": "log",
                "action_config": {
                    "level": "INFO",
                    "message": "Starting infrastructure bootstrap",
                },
                "execution_order": 1,
                "is_critical": False,
                "timeout_ms": 1000,
                "retry_on_failure": False,
            }
        }
