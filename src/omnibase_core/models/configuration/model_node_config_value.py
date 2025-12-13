"""Model for node configuration schema."""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_node_config_entry import (
    ConfigValue,
    ModelNodeConfigEntry,
)

__all__ = ["ConfigValue", "ModelNodeConfigEntry", "ModelNodeConfigSchema"]


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
