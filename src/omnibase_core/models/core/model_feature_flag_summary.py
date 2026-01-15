"""
Feature Flag Summary Model.

Summary of feature flag state including counts and flag names.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelFeatureFlagSummary(BaseModel):
    """Summary of feature flag state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total_flags: int = Field(default=0, description="Total number of flags")
    enabled_flags: int = Field(default=0, description="Number of enabled flags")
    disabled_flags: int = Field(default=0, description="Number of disabled flags")
    default_enabled: bool = Field(default=False, description="Default state for flags")
    enabled_flag_names: list[str] = Field(
        default_factory=list, description="Names of enabled flags"
    )
    disabled_flag_names: list[str] = Field(
        default_factory=list, description="Names of disabled flags"
    )
