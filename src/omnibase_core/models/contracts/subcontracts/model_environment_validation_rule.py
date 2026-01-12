"""
Environment Validation Rule Model.

Strongly-typed model for environment-specific validation rules.
Replaces dict[str, str] nested structures with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_environment_validation_rule_type import (
    EnumEnvironmentValidationRuleType,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEnvironmentValidationRule(BaseModel):
    """
    Strongly-typed environment-specific validation rule.

    Defines validation rules specific to a configuration key within
    a particular environment.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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

    min_value: float | None = Field(
        default=None,
        description="Minimum value constraint (for numeric/comparable types)",
    )

    max_value: float | None = Field(
        default=None,
        description="Maximum value constraint (for numeric/comparable types)",
    )

    format_pattern: str | None = Field(
        default=None,
        description="Regex pattern for format validation",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_rule_specific_fields(self) -> "ModelEnvironmentValidationRule":
        """
        Validate that field combinations are consistent with rule_type.

        Ensures that:
        - RANGE rules have at least min_value or max_value set
        - ALLOWED_VALUES rules have non-empty allowed_values list
        - FORMAT rules have format_pattern set

        Raises:
            ModelOnexError: If required fields are missing for the rule type
        """
        if self.rule_type == EnumEnvironmentValidationRuleType.RANGE:
            if self.min_value is None and self.max_value is None:
                raise ModelOnexError(
                    message="RANGE rule requires at least min_value or max_value to be set",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )
        elif self.rule_type == EnumEnvironmentValidationRuleType.ALLOWED_VALUES:
            if not self.allowed_values:
                raise ModelOnexError(
                    message="ALLOWED_VALUES rule requires non-empty allowed_values list",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )
        elif self.rule_type == EnumEnvironmentValidationRuleType.FORMAT:
            if not self.format_pattern:
                raise ModelOnexError(
                    message="FORMAT rule requires format_pattern to be set",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )

        return self
