"""
FSM Transition Action Model - ONEX Standards Compliant.

Individual model for FSM transition action specification.
Part of the FSM Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError


class ModelActionConfigValue(BaseModel):
    """
    Discriminated union for action configuration values.

    Replaces dict[str, PrimitiveValueType | list[str]] with proper type safety.
    """

    value_type: Literal["scalar", "list"] = Field(
        ...,
        description="Type of configuration value",
    )

    scalar_value: str | None = Field(
        default=None,
        description="Single string value (when value_type='scalar')",
    )

    list_value: list[str] | None = Field(
        default=None,
        description="List of string values (when value_type='list')",
    )

    @field_validator("scalar_value", "list_value", mode="after")
    @classmethod
    def validate_value_consistency(cls, v: Any, info: ValidationInfo) -> Any:
        """Ensure only one value type is set based on value_type."""
        if not hasattr(info, "data") or not info.data:
            return v

        value_type = info.data.get("value_type")
        field_name = info.field_name

        if value_type == "scalar" and field_name == "scalar_value":
            if v is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="scalar_value must be provided when value_type='scalar'",
                )
        elif value_type == "scalar" and field_name == "list_value":
            if v is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="list_value must be None when value_type='scalar'",
                )
        elif value_type == "list" and field_name == "list_value":
            if v is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="list_value must be provided when value_type='list'",
                )
        elif value_type == "list" and field_name == "scalar_value":
            if v is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="scalar_value must be None when value_type='list'",
                )

        return v

    def get_value(self) -> str | list[str]:
        """Get the actual value based on the value type."""
        if self.value_type == "scalar":
            return self.scalar_value or ""
        if self.value_type == "list":
            return self.list_value or []
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid value_type: {self.value_type}",
        )


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions,
    including logging, validation, and state modifications.
    """

    action_name: str = Field(
        ...,
        description="Unique name for the action",
        min_length=1,
    )

    action_type: str = Field(
        ...,
        description="Type of action (log, validate, modify, event, cleanup)",
        min_length=1,
    )

    action_config: dict[str, ModelActionConfigValue] = Field(
        default_factory=dict,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
