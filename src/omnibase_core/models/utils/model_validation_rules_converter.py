"""
ModelValidationRulesConverter - Shared Validation Rules Conversion Utility.

Provides unified conversion logic for flexible validation rule formats across
all contract models, eliminating code duplication and ensuring consistency.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, assert_never

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.core.type_constraints import PrimitiveValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_rules_input_type import (
    EnumValidationRulesInputType,
)
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules


# ONEX-compliant discriminated union for validation rules input - replaces Union pattern
class ModelValidationRulesInputValue(BaseModel):
    """
    Discriminated union for validation rules input values.

    Replaces Union[None, dict[str, object], ModelValidationRules, str] with
    ONEX-compliant discriminated union pattern.
    """

    input_type: EnumValidationRulesInputType = Field(
        description="Validation rules input type discriminator"
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
            raise ValueError(
                f"Field {field_name} is required for input type {input_type}"
            )

        return v

    @classmethod
    def from_none(cls) -> "ModelValidationRulesInputValue":
        """Create empty validation rules input."""
        return cls(input_type=EnumValidationRulesInputType.NONE)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ModelValidationRulesInputValue":
        """Create validation rules input from dictionary."""
        return cls(input_type=EnumValidationRulesInputType.DICT_OBJECT, dict_data=data)

    @classmethod
    def from_validation_rules(
        cls, rules: ModelValidationRules
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
            input_type=EnumValidationRulesInputType.STRING, string_constraint=constraint
        )

    @classmethod
    def from_any(cls, data: object) -> "ModelValidationRulesInputValue":
        """Create validation rules input from any supported type with automatic detection."""
        if data is None:
            return cls.from_none()
        elif isinstance(data, dict):
            return cls.from_dict(data)
        elif isinstance(data, ModelValidationRules):
            return cls.from_validation_rules(data)
        elif isinstance(data, str):
            return cls.from_string(data)

        # This should never be reached given the type annotations
        raise TypeError(f"Unsupported data type: {type(data)}")

    def is_empty(self) -> bool:
        """Check if validation rules input is empty."""
        return self.input_type == EnumValidationRulesInputType.NONE


class ModelValidationRulesConverter:
    """
    Shared utility for converting flexible validation rule formats.

    Eliminates code duplication across contract models by providing
    consistent validation rule conversion logic.
    """

    @staticmethod
    def convert_to_validation_rules(v: object) -> ModelValidationRules:
        """
        Convert validation rules input to ModelValidationRules.

        Uses discriminated union pattern for type-safe input handling.
        Accepts any object and converts it through the discriminated union.

        Args:
            v: Validation rules input in any supported format

        Returns:
            ModelValidationRules: Converted validation rules

        Raises:
            OnexError: If input format is not supported
        """
        try:
            # Handle discriminated union format directly
            if isinstance(v, ModelValidationRulesInputValue):
                return (
                    ModelValidationRulesConverter._convert_discriminated_union_to_rules(
                        v
                    )
                )

            # For all other types, convert to discriminated union first
            # This handles: None, dict[str, object], ModelValidationRules, str
            if v is None or isinstance(v, (dict, ModelValidationRules, str)):
                discriminated_input = ModelValidationRulesInputValue.from_any(v)
                return (
                    ModelValidationRulesConverter._convert_discriminated_union_to_rules(
                        discriminated_input
                    )
                )

            # This should never be reached due to type checking
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported validation rules format: {type(v)}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                    }
                ),
            )
        except (TypeError, ValueError) as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to convert validation rules: {str(e)}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("conversion_error"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "original_type": ModelSchemaValue.from_value(str(type(v))),
                    }
                ),
            ) from e

    @staticmethod
    def _convert_discriminated_union_to_rules(
        v: ModelValidationRulesInputValue,
    ) -> ModelValidationRules:
        """Convert discriminated union to ModelValidationRules."""
        if v.input_type == EnumValidationRulesInputType.NONE:
            return ModelValidationRules()
        elif (
            v.input_type == EnumValidationRulesInputType.DICT_OBJECT
            and v.dict_data is not None
        ):
            return ModelValidationRulesConverter._convert_dict_to_rules(v.dict_data)
        elif (
            v.input_type == EnumValidationRulesInputType.MODEL_VALIDATION_RULES
            and v.validation_rules is not None
        ):
            return v.validation_rules
        elif (
            v.input_type == EnumValidationRulesInputType.STRING
            and v.string_constraint is not None
        ):
            return ModelValidationRulesConverter._convert_string_to_rules(
                v.string_constraint
            )
        else:
            return ModelValidationRules()

    @staticmethod
    def _convert_dict_to_rules(v: dict[str, object]) -> ModelValidationRules:
        """Convert dict to ModelValidationRules (simplified from overly complex union handling)."""
        # Extract known boolean fields from dict with proper type casting
        strict_typing_enabled = bool(v.get("strict_typing_enabled", True))
        input_validation_enabled = bool(v.get("input_validation_enabled", True))
        output_validation_enabled = bool(v.get("output_validation_enabled", True))
        performance_validation_enabled = bool(
            v.get("performance_validation_enabled", True)
        )

        # Handle constraint definitions separately
        constraint_definitions: dict[str, str] = {}
        if "constraint_definitions" in v and isinstance(
            v["constraint_definitions"], dict
        ):
            constraint_definitions = {
                str(k): str(val) for k, val in v["constraint_definitions"].items()
            }

        return ModelValidationRules(
            strict_typing_enabled=strict_typing_enabled,
            input_validation_enabled=input_validation_enabled,
            output_validation_enabled=output_validation_enabled,
            performance_validation_enabled=performance_validation_enabled,
            constraint_definitions=constraint_definitions,
        )

    @staticmethod
    def _convert_string_to_rules(v: str) -> ModelValidationRules:
        """Convert string to ModelValidationRules with single constraint (simplified from primitives)."""
        constraints = {"rule_0": v}
        return ModelValidationRules(constraint_definitions=constraints)
