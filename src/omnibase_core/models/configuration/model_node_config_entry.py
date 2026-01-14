"""Model for node configuration entry."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.configuration.model_config_types import (
    VALID_VALUE_TYPES,
    ScalarConfigValue,
    validate_config_value_type,
)


class ModelNodeConfigEntry(BaseModel):
    """
    Strongly-typed model for a node configuration entry.

    This model represents a single configuration entry with its key,
    type information, and default value.

    Attributes:
        key: Configuration key (e.g., "compute.max_parallel_workers")
        value_type: Type name of the value ('int', 'float', 'bool', 'str')
        default: Default value for this configuration
    """

    key: str = Field(
        ...,
        description="Configuration key (e.g., 'compute.max_parallel_workers')",
    )
    value_type: VALID_VALUE_TYPES = Field(
        ...,
        description="Type name of the value ('int', 'float', 'bool', 'str')",
    )
    default: ScalarConfigValue = Field(
        ...,
        description="Default value for this configuration",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @model_validator(mode="after")
    def validate_default_type(self) -> "ModelNodeConfigEntry":
        """Ensure default value type matches declared value_type."""
        validate_config_value_type(self.value_type, self.default)
        return self
