"""
ModelValidationRulesInputValue - Discriminated Union for Validation Rules Input.

ONEX-compatible discriminated union that replaces Union pattern for validation rules.
"""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_rules_input_type import (
    EnumValidationRulesInputType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelValidationRulesInputValue(BaseModel):
    """
    Discriminated union for validation rules input values.

    Replaces Union[None, dict[str, object], ModelValidationRules, str] with
    ONEX-compatible discriminated union pattern.
    """

    model_config = ConfigDict(from_attributes=True)

    input_type: EnumValidationRulesInputType = Field(
        description="Validation rules input type discriminator",
    )

    # Data storage fields (only one should be populated based on input_type)
    dict_data: dict[str, ModelSchemaValue] | None = None
    validation_rules: ModelValidationRules | None = None
    string_constraint: str | None = None

    @field_validator("dict_data", "validation_rules", "string_constraint")
    @classmethod
    def validate_required_fields(cls, v: Any, info: ValidationInfo) -> Any:
        """Ensure required fields are present for each input type."""
        if not hasattr(info, "data") or "input_type" not in info.data:
            return v

        input_type = info.data["input_type"]
        field_name = info.field_name

        required_fields = {
            EnumValidationRulesInputType.NONE: None,  # No specific required field
            EnumValidationRulesInputType.DICT_OBJECT: "dict_data",
            EnumValidationRulesInputType.MODEL_VALIDATION_RULES: "validation_rules",
            EnumValidationRulesInputType.STRING: "string_constraint",
        }

        required_field = required_fields.get(input_type)
        if required_field == field_name and v is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Field {field_name} is required for input type {input_type}",
            )

        return v

    @classmethod
    def from_none(cls) -> "ModelValidationRulesInputValue":
        """Create empty validation rules input."""
        return cls(input_type=EnumValidationRulesInputType.NONE)

    @classmethod
    def from_dict(
        cls, data: dict[str, object] | dict[str, ModelSchemaValue]
    ) -> "ModelValidationRulesInputValue":
        """Create validation rules input from dictionary."""
        # Convert to ModelSchemaValue if needed
        if (
            data
            and len(data) > 0
            and not isinstance(next(iter(data.values())), ModelSchemaValue)
        ):
            converted_data: dict[str, ModelSchemaValue] = {
                k: ModelSchemaValue.from_value(v) for k, v in data.items()
            }
            return cls(
                input_type=EnumValidationRulesInputType.DICT_OBJECT,
                dict_data=converted_data,
            )
        # Data is already dict[str, ModelSchemaValue] since we checked the first value
        return cls(
            input_type=EnumValidationRulesInputType.DICT_OBJECT,
            dict_data=cast(dict[str, ModelSchemaValue], data),
        )

    @classmethod
    def from_validation_rules(
        cls,
        rules: ModelValidationRules,
    ) -> "ModelValidationRulesInputValue":
        """Create validation rules input from ModelValidationRules."""
        return cls(
            input_type=EnumValidationRulesInputType.MODEL_VALIDATION_RULES,
            validation_rules=rules,
        )

    @classmethod
    def from_string(cls, constraint: str) -> "ModelValidationRulesInputValue":
        """Create validation rules input from string constraint."""
        return cls(
            input_type=EnumValidationRulesInputType.STRING,
            string_constraint=constraint,
        )

    @classmethod
    def from_any(cls, data: object) -> "ModelValidationRulesInputValue":
        """Create validation rules input from any supported type with automatic detection."""
        if data is None:
            return cls.from_none()
        if isinstance(data, dict):
            return cls.from_dict(data)
        if isinstance(data, ModelValidationRules):
            return cls.from_validation_rules(data)
        if isinstance(data, str):
            return cls.from_string(data)

        # This should never be reached given the type annotations
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported data type: {type(data)}",
        )

    def is_empty(self) -> bool:
        """Check if validation rules input is empty."""
        return self.input_type == EnumValidationRulesInputType.NONE
