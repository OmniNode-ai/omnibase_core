"""
Configuration Validation Model.

Model for configuration validation rules and constraints in the ONEX configuration management system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_environment_validation_rules import ModelEnvironmentValidationRules
from .model_validation_schema_rule import ModelValidationSchemaRule


class ModelConfigurationValidation(BaseModel):
    """Configuration validation rules and constraints."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    required_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that must be present",
    )

    optional_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that are optional",
    )

    validation_schema: list[ModelValidationSchemaRule] = Field(
        default_factory=list,
        description="Strongly-typed validation rules for configuration values",
    )

    environment_specific: list[ModelEnvironmentValidationRules] = Field(
        default_factory=list,
        description="Strongly-typed environment-specific validation rules",
    )

    sensitive_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that contain sensitive data",
    )
