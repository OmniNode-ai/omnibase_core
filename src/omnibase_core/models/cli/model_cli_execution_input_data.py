"""
CLI Execution Input Data Model.

Represents input data for CLI execution with proper validation.
Replaces dict[str, Any] for input data with structured typing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_data_type import EnumDataType


class ModelCliExecutionInputData(BaseModel):
    """
    Structured input data for CLI execution.

    Replaces dict[str, Any] for input_data to provide
    type safety and validation for execution inputs.
    """

    # Data identification
    key: str = Field(..., description="Input data key identifier")
    value: Any = Field(
        ..., description="Input data value - supports str, int, bool, float, Path, UUID, list[str]"
    )

    # Data metadata
    data_type: EnumDataType = Field(..., description="Type of input data")
    is_sensitive: bool = Field(default=False, description="Whether data is sensitive")
    is_required: bool = Field(default=False, description="Whether data is required")

    # Validation
    description: str = Field(default="", description="Data description")
    validation_pattern: str = Field(
        default="", description="Regex pattern for validation"
    )

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, Path):
            return str(self.value)
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> Any:
        """Get the properly typed value."""
        return self.value

    def is_path_value(self) -> bool:
        """Check if this is a Path value."""
        return isinstance(self.value, Path)

    def is_uuid_value(self) -> bool:
        """Check if this is a UUID value."""
        return isinstance(self.value, UUID)


# Export for use
__all__ = ["ModelCliExecutionInputData"]
