"""
ModelValidationRulesConverter - Shared Validation Rules Conversion Utility.

Provides unified conversion logic for flexible validation rule formats across
all contract models, eliminating code duplication and ensuring consistency.

Strict typing is enforced - no Any types allowed in implementation.
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_rules_input_type import (
    EnumValidationRulesInputType,
)
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_validation_rules_input_value import (
    ModelValidationRulesInputValue,
)


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
            ModelOnexError: If input format is not supported
        """
        try:
            # Handle discriminated union format directly
            if isinstance(v, ModelValidationRulesInputValue):
                return (
                    ModelValidationRulesConverter._convert_discriminated_union_to_rules(
                        v,
                    )
                )

            # For all other types, convert to discriminated union first
            # This handles: None, dict[str, object], ModelValidationRules, str
            if v is None or isinstance(v, (dict, ModelValidationRules, str)):
                discriminated_input = ModelValidationRulesInputValue.from_any(v)
                return (
                    ModelValidationRulesConverter._convert_discriminated_union_to_rules(
                        discriminated_input,
                    )
                )

            # This should never be reached due to type checking
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported validation rules format: {type(v)}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        except (TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to convert validation rules: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("conversion_error"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "original_type": ModelSchemaValue.from_value(str(type(v))),
                    },
                ),
            ) from e

    @staticmethod
    def _convert_discriminated_union_to_rules(
        v: ModelValidationRulesInputValue,
    ) -> ModelValidationRules:
        """Convert discriminated union to ModelValidationRules."""
        if v.input_type == EnumValidationRulesInputType.NONE:
            return ModelValidationRules()
        if (
            v.input_type == EnumValidationRulesInputType.DICT_OBJECT
            and v.dict_data is not None
        ):
            # Convert ModelSchemaValue to raw values for dict processing
            raw_dict: dict[str, object] = {
                k: val.to_value() for k, val in v.dict_data.items()
            }
            return ModelValidationRulesConverter._convert_dict_to_rules(raw_dict)
        if (
            v.input_type == EnumValidationRulesInputType.MODEL_VALIDATION_RULES
            and v.validation_rules is not None
        ):
            return v.validation_rules
        if (
            v.input_type == EnumValidationRulesInputType.STRING
            and v.string_constraint is not None
        ):
            return ModelValidationRulesConverter._convert_string_to_rules(
                v.string_constraint,
            )
        return ModelValidationRules()

    @staticmethod
    def _convert_dict_to_rules(v: dict[str, object]) -> ModelValidationRules:
        """Convert dict to ModelValidationRules (simplified from overly complex union handling)."""
        # Extract known boolean fields from dict with proper type casting
        strict_typing_enabled = bool(v.get("strict_typing_enabled", True))
        input_validation_enabled = bool(v.get("input_validation_enabled", True))
        output_validation_enabled = bool(v.get("output_validation_enabled", True))
        performance_validation_enabled = bool(
            v.get("performance_validation_enabled", True),
        )

        # Handle constraint definitions separately
        constraint_definitions: dict[str, str] = {}
        if "constraint_definitions" in v and isinstance(
            v["constraint_definitions"],
            dict,
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
