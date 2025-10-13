from typing import Any

from pydantic import Field

"""
FSM Operation Model - ONEX Standards Compliant.

Individual model for FSM operation specification.
Part of the FSM Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel


class ModelFSMOperation(BaseModel):
    """
    Operation specification for FSM subcontract.

    Defines available operations for state transitions,
    constraints, and atomic operation guarantees.
    """

    operation_name: str = Field(
        default=...,
        description="Unique name for the operation",
        min_length=1,
    )

    operation_type: str = Field(
        default=...,
        description="Type of operation (create, update, delete, transition, snapshot, restore)",
        min_length=1,
    )

    description: str = Field(
        default=...,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
