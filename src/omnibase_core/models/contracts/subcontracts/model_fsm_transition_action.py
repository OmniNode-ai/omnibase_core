from typing import List, Literal

from pydantic import Field, ValidationInfo, field_validator

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
FSM Transition Action Model - ONEX Standards Compliant.

Individual model for FSM transition action specification.
Part of the FSM Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.errors.error_codes import EnumCoreErrorCode

from .model_fsmtransitionaction import ModelFSMTransitionAction


class ModelActionConfigValue(BaseModel):
    """
    Discriminated union for action configuration values.

    Replaces dict[str, PrimitiveValueType | list[str]] with proper type safety.
    """

    value_type: Literal["scalar", "list[Any]"] = Field(
        default=...,
        description="Type of configuration value",
    )

    scalar_value: str | None = Field(
        default=None,
        description="Single string value (when value_type='scalar')",
    )

    list_value: list[str] | None = Field(
        default=None,
        description="List of string values (when value_type='list[Any]')",
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
                raise ModelOnexError(
                    message="scalar_value must be provided when value_type='scalar'",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        elif value_type == "scalar" and field_name == "list_value":
            if v is not None:
                raise ModelOnexError(
                    message="list_value must be None when value_type='scalar'",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        elif value_type == "list[Any]" and field_name == "list_value":
            if v is None:
                raise ModelOnexError(
                    message="list_value must be provided when value_type='list[Any]'",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        elif value_type == "list[Any]" and field_name == "scalar_value":
            if v is not None:
                raise ModelOnexError(
                    message="scalar_value must be None when value_type='list[Any]'",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        return v

    def get_value(self) -> str | list[str]:
        """Get the actual value based on the value type."""
        if self.value_type == "scalar":
            return self.scalar_value or ""
        if self.value_type == "list[Any]":
            return self.list_value or []
        raise ModelOnexError(
            message=f"Invalid value_type: {self.value_type}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
