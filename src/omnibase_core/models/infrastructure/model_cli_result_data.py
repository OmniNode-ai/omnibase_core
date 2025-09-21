"""
CLI result data model.

CLI result data model with typed fields for command execution results.
Follows ONEX one-model-per-file naming conventions.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from ..core.model_custom_properties import ModelCustomProperties


class ModelCliResultData(BaseModel):
    """CLI result data model with typed fields."""

    success: bool = Field(description="Whether execution was successful")
    execution_id: UUID = Field(description="Execution identifier")
    output_data: (
        str
        | int
        | float
        | bool
        | dict[str, str | int | float | bool]
        | list[str | int | float | bool]
        | None
    ) = Field(description="Output data if successful")
    error_message: str | None = Field(description="Error message if failed")
    tool_name: str | None = Field(description="Tool name if available")
    execution_time_ms: int | None = Field(description="Execution time in milliseconds")
    status_code: int = Field(description="Status code")
    warnings: list[str] = Field(description="Warning messages")
    metadata: ModelCustomProperties = Field(description="Execution metadata")


# Export for use
__all__ = ["ModelCliResultData"]
