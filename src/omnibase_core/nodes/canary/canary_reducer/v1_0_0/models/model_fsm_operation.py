"""
ModelFSMOperation - Operation definition for FSM capabilities.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides operation specification including permissions, constraints, and side effects.
"""

from enum import Enum

from pydantic import BaseModel, Field


class FSMOperationType(str, Enum):
    """Type classification of FSM operations."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    TRANSITION = "transition"
    SNAPSHOT = "snapshot"
    RESTORE = "restore"


class FSMSideEffect(str, Enum):
    """Side effects of FSM operations."""

    STATE_CHANGE = "state_change"
    RESOURCE_ALLOCATION = "resource_allocation"
    EVENT_EMISSION = "event_emission"
    STORAGE_WRITE = "storage_write"
    NETWORK_CALL = "network_call"


class FSMPerformanceImpact(str, Enum):
    """Performance impact classification of operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelFSMOperation(BaseModel):
    """
    Operation that can be performed within the FSM.

    Defines operations available in the finite state machine including:
    - Operation identification and classification
    - State constraints and permissions
    - Side effects and performance impact
    - Timeout and atomicity requirements
    """

    # Core identification
    operation_name: str = Field(
        ...,
        description="Unique identifier for the operation",
        pattern=r"^[a-z][a-z0-9_]*$",
        min_length=1,
        max_length=50,
    )

    operation_type: FSMOperationType = Field(
        ...,
        description="Type classification of the operation",
    )

    description: str = Field(
        ...,
        description="Human-readable description of the operation",
        min_length=10,
        max_length=200,
    )

    # Operation requirements
    requires_atomic_execution: bool = Field(
        ...,
        description="Whether this operation must execute atomically",
    )

    supports_rollback: bool = Field(
        ...,
        description="Whether this operation supports rollback",
    )

    # State constraints
    allowed_from_states: list[str] = Field(
        default_factory=list,
        description="States from which this operation can be executed",
    )

    blocked_from_states: list[str] = Field(
        default_factory=list,
        description="States from which this operation is blocked",
    )

    # Security and permissions
    required_permissions: list[str] = Field(
        default_factory=list,
        description="Permissions required to execute this operation",
    )

    # Operation characteristics
    side_effects: list[FSMSideEffect] = Field(
        default_factory=list,
        description="Side effects of executing this operation",
    )

    performance_impact: FSMPerformanceImpact = Field(
        default=FSMPerformanceImpact.LOW,
        description="Performance impact classification",
    )

    timeout_ms: int = Field(
        default=30000,
        description="Timeout for operation execution in milliseconds",
        ge=1000,
        le=300000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "operation_name": "create",
                "operation_type": "create",
                "description": "Create new infrastructure state",
                "requires_atomic_execution": True,
                "supports_rollback": True,
                "allowed_from_states": ["idle"],
                "blocked_from_states": ["disabled"],
                "required_permissions": ["infrastructure_create"],
                "side_effects": ["state_change", "resource_allocation"],
                "performance_impact": "medium",
                "timeout_ms": 30000,
            },
        }
