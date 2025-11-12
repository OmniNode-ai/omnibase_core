"""
Environment Validation Rule Model - ONEX Standards Compliant.

Strongly-typed model for environment-specific validation rules.
Replaces dict[str, str] nested structures with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_environment_validation_rule_type import (
    EnumEnvironmentValidationRuleType,
)


class ModelEnvironmentValidationRule(BaseModel):
    """
    Strongly-typed environment-specific validation rule.

    Defines validation rules specific to a configuration key within
    a particular environment.
    """

    config_key: str = Field(
        ...,
        description="Configuration key name",
        min_length=1,
    )

    validation_rule: str = Field(
        ...,
        description="Validation rule for this key in this environment",
        min_length=1,
    )

    rule_type: EnumEnvironmentValidationRuleType = Field(
        default=EnumEnvironmentValidationRuleType.VALUE_CHECK,
        description="Type of validation (value_check, format, range, allowed_values)",
    )

    allowed_values: list[str] = Field(
        default_factory=list,
        description="List of allowed values for this key in this environment",
    )

    min_value: str | None = Field(
        default=None,
        description="Minimum value constraint (for numeric/comparable types)",
    )

    max_value: str | None = Field(
        default=None,
        description="Maximum value constraint (for numeric/comparable types)",
    )

    format_pattern: str | None = Field(
        default=None,
        description="Regex pattern for format validation",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
