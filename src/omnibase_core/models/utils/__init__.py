"""
Utility models for YAML processing, contract validation, and data conversion.

This module provides utility models that support core ONEX operations including
YAML serialization, contract validation, and field conversion between different
representations.

Key Components:
    ModelYamlDumpOptions:
        Type-safe configuration for YAML serialization with options for
        formatting, indentation, and encoding.

    ModelYamlOption:
        Individual YAML configuration option with type and default value.

    ModelYamlValue:
        Typed wrapper for YAML values with validation and conversion support.

    ModelFieldConverterRegistry:
        Registry for field converters that transform data between different
        representations (e.g., model to dict, dict to YAML).

    FieldConverter:
        Protocol for implementing custom field conversion logic.

    ModelSubcontractConstraintValidator:
        Validator for ensuring subcontract constraints are satisfied during
        contract validation.

Usage Notes:
    - ModelValidationRulesConverter is intentionally excluded from this module
      to avoid circular imports. Import it directly when needed:
      ``from omnibase_core.models.utils.model_validation_rules_converter import ModelValidationRulesConverter``

Example:
    >>> from omnibase_core.models.utils import ModelYamlDumpOptions
    >>>
    >>> # Configure YAML output formatting
    >>> yaml_options = ModelYamlDumpOptions(
    ...     indent=4,
    ...     sort_keys=True,
    ...     allow_unicode=True,
    ... )

See Also:
    - omnibase_core.utils.yaml_utils: YAML utility functions
    - omnibase_core.models.contracts: Contract model definitions
"""

from .model_field_converter import FieldConverter, ModelFieldConverterRegistry
from .model_subcontract_constraint_validator import ModelSubcontractConstraintValidator
from .model_yaml_dump_options import ModelYamlDumpOptions
from .model_yaml_option import ModelYamlOption
from .model_yaml_value import ModelYamlValue

# ModelValidationRulesConverter not imported here to avoid circular import
# Import it directly where needed: from omnibase_core.models.utils.model_validation_rules_converter import ModelValidationRulesConverter

__all__ = [
    "FieldConverter",
    "ModelFieldConverterRegistry",
    "ModelSubcontractConstraintValidator",
    "ModelYamlDumpOptions",
    "ModelYamlOption",
    "ModelYamlValue",
    # "ModelValidationRulesConverter",  # Excluded to break circular import
]
