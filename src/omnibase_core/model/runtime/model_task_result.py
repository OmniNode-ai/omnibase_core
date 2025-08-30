"""
Task Result Models

ONEX-compliant models for task execution results with strong typing.
"""

from typing import Union

from pydantic import BaseModel, Field


class ModelTaskResult(BaseModel):
    """Strongly-typed task execution result."""

    success: bool
    message: str
    data: str = Field(default="", description="Task result data as string")
    error_details: str = Field(default="", description="Error details if task failed")

    @classmethod
    def from_execution(
        cls, result_data: Union[str, int, float, bool, None]
    ) -> "ModelTaskResult":
        """Create task result from execution data."""
        if result_data is None:
            return cls(success=True, message="Task completed successfully", data="")

        return cls(
            success=True, message="Task completed successfully", data=str(result_data)
        )

    @classmethod
    def from_error(cls, error_message: str) -> "ModelTaskResult":
        """Create task result from error."""
        return cls(
            success=False, message="Task execution failed", error_details=error_message
        )
