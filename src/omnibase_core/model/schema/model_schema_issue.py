"""
Schema Issue Model.

Individual schema issue model.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelSchemaIssue(BaseModel):
    """Individual schema issue."""

    severity: str = Field(..., description="Issue severity level")
    message: str = Field(..., description="Issue description")
    schema_path: Optional[str] = Field(None, description="Path to schema file")
    line_number: Optional[int] = Field(None, description="Line number in schema")
    field_path: Optional[str] = Field(
        None, description="JSON path to problematic field"
    )
