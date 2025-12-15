"""
FSM State Definition Model.

Schema version: v1.5.0

Individual model for FSM state definition.
Part of the FSM Subcontract Model family.

This model defines state properties, lifecycle management,
and validation rules for FSM state handling.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMStateDefinition(BaseModel):
    """
    State definition for FSM subcontract.

    Defines state properties, lifecycle management,
    and validation rules for FSM state handling.

    Schema Version:
        v1.5.0 - Added frozen=True for immutability after creation.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees.

    Validation Rules:
        - Terminal states cannot have is_recoverable=True (logical contradiction)

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    state_name: str = Field(
        default=..., description="Unique name for the state", min_length=1
    )

    state_type: str = Field(
        default=...,
        description="Type classification (operational, snapshot, error, terminal)",
        min_length=1,
    )

    description: str = Field(
        default=...,
        description="Human-readable state description",
        min_length=1,
    )

    is_terminal: bool = Field(
        default=False,
        description="Whether this is a terminal/final state",
    )

    is_recoverable: bool = Field(
        default=True,
        description="Whether recovery is possible from this state",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Maximum time allowed in this state (reserved for v1.1+)",
        ge=1,
    )

    entry_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state entry",
    )

    exit_actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute on state exit",
    )

    required_data: list[str] = Field(
        default_factory=list,
        description="Required data fields for this state",
    )

    optional_data: list[str] = Field(
        default_factory=list,
        description="Optional data fields for this state",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Validation rules for state data",
    )

    @model_validator(mode="after")
    def validate_terminal_not_recoverable(self) -> "ModelFSMStateDefinition":
        """Validate that terminal states cannot have is_recoverable=True.

        Terminal states represent completed workflows that cannot be re-entered.
        Having is_recoverable=True on a terminal state is a logical contradiction.

        Returns:
            The validated instance (self).

        Raises:
            ModelOnexError: If a terminal state has is_recoverable=True.
        """
        if self.is_terminal and self.is_recoverable:
            raise ModelOnexError(
                message=(
                    f"Terminal state '{self.state_name}' cannot have "
                    "is_recoverable=True. Terminal states represent completed "
                    "workflows that cannot be recovered."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        from_attributes=True,  # Allow validation via attribute access for nested models
    )
