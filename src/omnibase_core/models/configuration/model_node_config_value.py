"""Model for node configuration values."""

from pydantic import BaseModel, Field

# Type alias for valid configuration value types
ConfigValue = int | float | bool | str


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
    value_type: str = Field(
        ...,
        description="Type name of the value ('int', 'float', 'bool', 'str')",
    )
    default: ConfigValue = Field(
        ...,
        description="Default value for this configuration",
    )

    model_config = {"frozen": True}


class ModelNodeConfigSchema(BaseModel):
    """
    Strongly-typed model for node configuration schema.

    Represents a complete configuration schema entry including
    key, type, and default value information.

    Attributes:
        key: Configuration key
        type: Type name of the value
        default: Default value
    """

    key: str = Field(..., description="Configuration key")
    type: str = Field(..., description="Type name of the value")
    default: ConfigValue = Field(..., description="Default value")

    model_config = {"frozen": True}
