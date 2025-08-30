# Generated from contract: tool_claude_code_response_models v1.0.0
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelEditToolResponse(BaseModel):
    """Structured response from Edit tool execution."""

    file_path: str = Field(..., description="Path to the file that was edited")
    replacements_made: int = Field(
        ..., description="Number of string replacements made", ge=0
    )
    old_string: str = Field(..., description="The string that was replaced")
    new_string: str = Field(..., description="The replacement string")
    replace_all: bool = Field(..., description="Whether all occurrences were replaced")
    lines_affected: List[int] = Field(
        ..., description="Line numbers that were modified"
    )
    file_size_before: int = Field(
        ..., description="File size before edit in bytes", ge=0
    )
    file_size_after: int = Field(..., description="File size after edit in bytes", ge=0)
    backup_created: bool = Field(
        default=False, description="Whether backup was created before edit"
    )
    backup_path: Optional[str] = Field(
        None, description="Path to backup file if created"
    )
    encoding: str = Field(default="utf-8", description="File encoding used")
