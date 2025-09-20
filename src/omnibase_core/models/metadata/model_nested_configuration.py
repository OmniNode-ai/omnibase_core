"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data."""

    config_name: str = Field(..., description="Configuration name")
    config_type: str = Field(..., description="Configuration type")
    settings: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Configuration settings with basic types only"
    )


# Export the model
__all__ = ["ModelNestedConfiguration"]
