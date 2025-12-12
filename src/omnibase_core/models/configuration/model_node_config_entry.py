"""Model for node configuration entry."""

from pydantic import BaseModel, Field

# Type alias for valid configuration value types
# IMPORTANT: bool MUST come before int because bool is a subclass of int in Python
# If int comes first, Pydantic will match True/False as 1/0 integers
ConfigValue = bool | int | float | str


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
