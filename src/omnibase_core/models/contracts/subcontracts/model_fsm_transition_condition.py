"""
FSM Transition Condition Model.

Schema version: v1.5.0

Individual model for FSM transition condition specification.
Part of the FSM Subcontract Model family.

This model defines condition types, expressions, and validation logic
for determining valid state transitions.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.

    Schema Version:
        v1.5.0 - Added frozen=True for immutability after creation.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees.

    Expression Grammar (v1.0):
        Expressions use a strict 3-token grammar: "field operator value"
        Supported operators: equals, not_equals, greater_than, less_than,
        min_length, max_length, exists, not_exists

    Required vs Optional Conditions:
        - required=True (default): Condition failure blocks transition
        - required=False: Condition failure is advisory, transition proceeds

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (MUST be provided in YAML contract)",
    )

    condition_name: str = Field(
        default=...,
        description="Unique name for the condition",
        min_length=1,
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (expression, custom)",
        min_length=1,
    )

    expression: str = Field(
        default=...,
        description="3-token condition expression: 'field operator value'",
        min_length=1,
    )

    required: bool = Field(
        default=True,
        description="Whether this condition is required for transition",
    )

    error_message: str | None = Field(
        default=None,
        description="Custom error message if condition fails",
    )

    retry_count: int = Field(
        default=0,
        description="Number of retries for failed conditions (reserved for v1.1+)",
        ge=0,
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for condition evaluation in milliseconds (reserved for v1.1+)",
        ge=1,
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Explicit - redundant with frozen=True but kept for clarity
    )
