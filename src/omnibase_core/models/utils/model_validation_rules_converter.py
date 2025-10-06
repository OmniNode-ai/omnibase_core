from typing import Union

from pydantic import Field, ValidationInfo, field_validator

from omnibase_core.errors.error_codes import ModelOnexError

"""
ModelValidationRulesConverter - Shared Validation Rules Conversion Utility.

Provides unified conversion logic for flexible validation rule formats across
all contract models, eliminating code duplication and ensuring consistency.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_validation_rules_input_type import (
    EnumValidationRulesInputType,
)
from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules

from .model_validationrulesconverter import ModelValidationRulesConverter


# ONEX-compliant discriminated union for validation rules input - replaces Union pattern
class ModelValidationRulesInputValue(BaseModel):
    """
    Discriminated union for validation rules input values.

    Replaces Union[None, dict[str, object], ModelValidationRules, str] with
    ONEX-compliant discriminated union pattern.
    """

    input_type: EnumValidationRulesInputType = Field(
        description="Validation rules input type discriminator",
    )

    # Data storage fields (only one should be populated based on input_type)
    dict_data: dict[str, object] | None = None
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
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Field {field_name} is required for input type {input_type}",
            )

        return v

    @classmethod
    def from_none(cls) -> "ModelValidationRulesInputValue":
        """Create empty validation rules input."""
        return cls(input_type=EnumValidationRulesInputType.NONE)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ModelValidationRulesInputValue":
        """Create validation rules input from dict[str, Any]ionary."""
        return cls(input_type=EnumValidationRulesInputType.DICT_OBJECT, dict_data=data)

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
            code=ModelCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported data type: {type(data)}",
        )

    def is_empty(self) -> bool:
        """Check if validation rules input is empty."""
        return self.input_type == EnumValidationRulesInputType.NONE
