"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_config_type import EnumConfigType
from ...utils.uuid_utilities import uuid_from_string


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data."""

    # UUID-based entity references
    config_id: UUID = Field(..., description="Unique identifier for the configuration")
    config_display_name: str | None = Field(
        None, description="Human-readable configuration name"
    )
    config_type: EnumConfigType = Field(
        ...,
        description="Configuration type",
    )
    settings: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Configuration settings with basic types only"
    )


# Export the model
__all__ = ["ModelNestedConfiguration"]
