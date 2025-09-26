#!/usr/bin/env python3
"""
ModelValidationRulesConverter - Shared Validation Rules Conversion Utility.

Provides unified conversion logic for flexible validation rule formats across
all contract models, eliminating code duplication and ensuring consistency.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Union, assert_never

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules

# Type alias for validation rules input - includes all possible input types
# Using ModelSchemaValue instead of Any for ONEX compliance
ValidationRulesInput = Union[
    None,
    dict[str, ModelSchemaValue],
    dict[str, object],
    list[ModelSchemaValue],
    list[object],
    ModelValidationRules,
    str,
    int,
    float,
    bool,
]


class ModelValidationRulesConverter:
    """
    Shared utility for converting flexible validation rule formats.

    Eliminates code duplication across contract models by providing
    consistent validation rule conversion logic.
    """

    @staticmethod
    def convert_to_validation_rules(v: ValidationRulesInput) -> ModelValidationRules:
        """
        Convert flexible validation rules format to ModelValidationRules.

        Handles all supported input formats:
        - None -> empty ModelValidationRules
        - dict -> ModelValidationRules with converted values
        - list -> ModelValidationRules with constraint_definitions
        - ModelValidationRules -> return as is
        - primitives -> wrap in ModelValidationRules

        Args:
            v: Validation rules input in any supported format

        Returns:
            ModelValidationRules: Converted validation rules

        Raises:
            ValueError: If input format is not supported
        """
        if v is None:
            return ModelValidationRules()

        if isinstance(v, dict):
            return ModelValidationRulesConverter._convert_dict_to_rules(v)

        if isinstance(v, list):
            return ModelValidationRulesConverter._convert_list_to_rules(v)

        # If already ModelValidationRules, return as is
        if isinstance(v, ModelValidationRules):
            return v

        # If it's a primitive value, wrap it in ModelValidationRules
        if isinstance(v, (str, int, float, bool)):
            return ModelValidationRulesConverter._convert_primitive_to_rules(v)

        # This should never be reached due to exhaustive type checking
        # Raise exception instead of assert_never to avoid MyPy no-any-return error
        raise ValueError(f"Unsupported validation rules format: {type(v)}")

    @staticmethod
    def _convert_dict_to_rules(
        v: Union[dict[str, ModelSchemaValue], dict[str, object]],
    ) -> ModelValidationRules:
        """Convert dict to ModelValidationRules."""
        # Handle ModelSchemaValue dict format (compute contract style)
        if v and isinstance(next(iter(v.values())), ModelSchemaValue):
            # Convert dict of ModelSchemaValue to raw values for ModelValidationRules
            raw_dict = {
                k: schema_val.to_value()
                for k, schema_val in v.items()
                if hasattr(schema_val, "to_value")
            }
            return ModelValidationRules(**raw_dict)

        # Handle regular object dict format (effect contract style)
        return ModelValidationRules(**v)

    @staticmethod
    def _convert_list_to_rules(
        v: Union[list[ModelSchemaValue], list[object]],
    ) -> ModelValidationRules:
        """Convert list to ModelValidationRules with constraint_definitions."""
        # Handle ModelSchemaValue list format
        if v and hasattr(v[0], "to_value"):
            constraints = {
                f"rule_{i}": str(rule.to_value())
                for i, rule in enumerate(v)
                if hasattr(rule, "to_value")
            }
        else:
            # Handle regular object list format
            constraints = {f"rule_{i}": str(rule) for i, rule in enumerate(v)}

        return ModelValidationRules(constraint_definitions=constraints)

    @staticmethod
    def _convert_primitive_to_rules(
        v: Union[str, int, float, bool],
    ) -> ModelValidationRules:
        """Convert primitive to ModelValidationRules with single constraint."""
        constraints = {"rule_0": str(v)}
        return ModelValidationRules(constraint_definitions=constraints)
