"""
Code location model for tracking entity positions in source code.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCodeLocation(BaseModel):
    """Model for code location metadata."""

    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    start_column: int = Field(..., description="Starting column number")
    end_column: int = Field(..., description="Ending column number")
    function_name: str | None = Field(
        None,
        description="Name of containing function",
    )
    class_name: str | None = Field(None, description="Name of containing class")
    module_name: str = Field(..., description="Name of containing module")
    scope_depth: int = Field(0, description="Nesting depth in code structure")

    model_config = ConfigDict(frozen=True, validate_assignment=True)
