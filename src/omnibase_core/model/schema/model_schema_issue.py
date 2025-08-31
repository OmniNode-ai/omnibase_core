"""
Schema Issue Model.

Individual schema issue model.
"""

from pydantic import BaseModel, Field


class ModelSchemaIssue(BaseModel):
    """Individual schema issue."""

    severity: str = Field(..., description="Issue severity level")
    message: str = Field(..., description="Issue description")
    schema_path: str | None = Field(None, description="Path to schema file")
    line_number: int | None = Field(None, description="Line number in schema")
    field_path: str | None = Field(
        None,
        description="JSON path to problematic field",
    )
