"""Model for node configuration schema."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.configuration.model_config_types import (
    VALID_VALUE_TYPES,
    ScalarConfigValue,
    validate_config_value_type,
)


class ModelNodeConfigSchema(BaseModel):
    """
    Strongly-typed model for node configuration schema.

    Represents a complete configuration schema entry including
    key, type, and default value information.

    Attributes:
        key: Configuration key
        config_type: Type name of the value ('int', 'float', 'bool', 'str')
        default: Default value
    """

    key: str = Field(..., description="Configuration key")
    config_type: VALID_VALUE_TYPES = Field(
        ..., alias="type", description="Type name of the value"
    )
    default: ScalarConfigValue = Field(..., description="Default value")

    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, from_attributes=True
    )

    @model_validator(mode="after")
    def validate_default_type(self) -> "ModelNodeConfigSchema":
        """Ensure default value type matches declared config_type."""
        validate_config_value_type(self.config_type, self.default)
        return self
