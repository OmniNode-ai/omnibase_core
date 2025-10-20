from typing import Any

from pydantic import Field

"""
Configuration Validation Model - ONEX Standards Compliant.

Model for configuration validation rules and constraints in the ONEX configuration management system.
"""

from pydantic import BaseModel

from omnibase_core.enums.enum_environment import EnumEnvironment


class ModelConfigurationValidation(BaseModel):
    """Configuration validation rules and constraints."""

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    required_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that must be present",
    )

    optional_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that are optional",
    )

    validation_schema: dict[str, str] | None = Field(
        default=None,
        description="JSON schema or validation rules for configuration values",
    )

    environment_specific: dict[EnumEnvironment, dict[str, str]] = Field(
        default_factory=dict,
        description="Environment-specific validation rules",
    )

    sensitive_keys: list[str] = Field(
        default_factory=list,
        description="Configuration keys that contain sensitive data",
    )
