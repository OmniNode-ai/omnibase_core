from pydantic import Field

"""
FSM Transition Condition Model - ONEX Standards Compliant.

Individual model for FSM transition condition specification.
Part of the FSM Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.
    """

    condition_name: str = Field(
        default=...,
        description="Unique name for the condition",
        min_length=1,
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (validation, state, processing, custom)",
        min_length=1,
    )

    expression: str = Field(
        default=...,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
