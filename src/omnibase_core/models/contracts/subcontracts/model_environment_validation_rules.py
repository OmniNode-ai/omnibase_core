"""
Environment Validation Rules Model - ONEX Standards Compliant.

Strongly-typed model for grouping environment-specific validation rules.
Replaces dict[EnumEnvironment, dict[str, str]] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_environment import EnumEnvironment

from .model_environment_validation_rule import ModelEnvironmentValidationRule


class ModelEnvironmentValidationRules(BaseModel):
    """
    Strongly-typed environment validation rules container.

    Groups validation rules by environment with proper type safety.
    Replaces nested dict structures with validated models.
    """

    environment: EnumEnvironment = Field(
        ...,
        description="Target environment for these validation rules",
    )

    validation_rules: list[ModelEnvironmentValidationRule] = Field(
        default_factory=list,
        description="List of validation rules for this environment",
    )

    inherit_from_default: bool = Field(
        default=True,
        description="Whether to inherit validation rules from default environment",
    )

    override_default: bool = Field(
        default=False,
        description="Whether these rules completely override default rules",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
