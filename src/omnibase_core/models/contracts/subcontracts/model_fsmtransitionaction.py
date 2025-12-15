"""
ModelFSMTransitionAction - Action specification for FSM state transitions.

Schema version: v1.5.0
Thread-safe: Yes (frozen=True)

This model defines actions to execute during state transitions,
including logging, validation, and state modifications.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access
        across multiple threads without synchronization.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (MUST be provided)",
    )

    action_name: str = Field(
        default=...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        default=...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: list[ModelActionConfigParameter] = Field(
        default_factory=list,
        description="Strongly-typed configuration parameters for the action",
    )

    execution_order: int = Field(
        default=1,
        description="Order of execution relative to other actions",
        ge=1,
    )

    is_critical: bool = Field(
        default=False,
        description="Whether action failure should abort transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Action to execute if rollback is needed",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Timeout for action execution",
        ge=1,
    )

    @model_validator(mode="after")
    def validate_unique_action_config(self) -> ModelFSMTransitionAction:
        """Ensure action_config parameter names are unique."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for param in self.action_config:
            if param.name in seen:
                duplicates.add(param.name)
            seen.add(param.name)
        if duplicates:
            raise ModelOnexError(
                message=f"Duplicate parameter names in action_config: {sorted(duplicates)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        frozen=True,  # Immutability after creation for thread safety
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        from_attributes=True,  # Allow validation via attribute access for nested models
    )
