# Generated from contract: tool_claude_code_response_models v1.0.0
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ModelNotebookEditToolResponse(BaseModel):
    """Structured response from NotebookEdit tool execution."""

    notebook_path: str = Field(..., description="Path to the notebook that was edited")
    cell_number: Optional[int] = Field(
        None, description="Cell number that was modified (0-indexed)"
    )
    cell_id: Optional[str] = Field(None, description="Cell ID that was modified")
    edit_mode: Literal["replace", "insert", "delete"] = Field(
        ..., description="Type of edit operation performed"
    )
    cell_type: Optional[Literal["code", "markdown"]] = Field(
        None, description="Type of cell that was modified"
    )
    success: bool = Field(..., description="Whether the edit operation succeeded")
    cells_modified: int = Field(default=1, description="Number of cells modified", ge=0)
    backup_created: bool = Field(
        default=False, description="Whether backup was created before edit"
    )
    backup_path: Optional[str] = Field(
        None, description="Path to backup file if created"
    )
    notebook_version: Optional[str] = Field(
        None, description="Jupyter notebook format version"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
