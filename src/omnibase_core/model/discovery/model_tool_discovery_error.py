"""Tool discovery error model for tracking discovery failures."""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_error_type import EnumErrorType


class ModelToolDiscoveryError(BaseModel):
    """Model for tool discovery errors with detailed tracking."""

    tool_path: str = Field(..., description="Path of the problematic tool")
    error_type: EnumErrorType = Field(..., description="Type of error encountered")
    error_message: str = Field(..., description="Detailed error message", min_length=1)
    discovery_timestamp: float = Field(
        ..., description="When the error was discovered", gt=0
    )
