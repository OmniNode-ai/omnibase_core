"""
Validation Schema Rule Model - ONEX Standards Compliant.

Strongly-typed model for configuration validation schema rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_validation_rule_type import EnumValidationRuleType


class ModelValidationSchemaRule(BaseModel):
    """
    Strongly-typed validation schema rule.

    Defines validation rules for configuration keys with type safety
    and runtime validation.
    """

    key_name: str = Field(
        ...,
        description="Configuration key name to validate",
        min_length=1,
    )

    validation_rule: str = Field(
        ...,
        description="Validation rule expression or JSON schema fragment",
        min_length=1,
    )

    rule_type: EnumValidationRuleType = Field(
        default=EnumValidationRuleType.REGEX,
        description="Type of validation rule (regex, json_schema, range, enum)",
    )

    error_message: str | None = Field(
        default=None,
        description="Custom error message for validation failures",
    )

    is_required: bool = Field(
        default=False,
        description="Whether this validation must pass",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
