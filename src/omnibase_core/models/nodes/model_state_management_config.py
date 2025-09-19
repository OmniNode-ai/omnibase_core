"""
State management configuration model for nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumStorageType


class ModelStateManagementConfig(BaseModel):
    """State management configuration."""

    model_config = ConfigDict(extra="forbid")

    persistence: bool = Field(
        default=False,
        description="Whether state should be persisted",
    )
    storage_type: EnumStorageType | None = Field(
        None,
        description="Storage type for state",
    )
    compression: bool = Field(
        default=False,
        description="Whether to compress stored state",
    )
    expiry_seconds: int | None = Field(
        None,
        description="State expiry time in seconds",
        ge=0,
    )
