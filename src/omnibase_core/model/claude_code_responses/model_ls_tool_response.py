# Generated from contract: tool_claude_code_response_models v1.0.0
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelDirectoryEntry(BaseModel):
    """Directory listing entry."""

    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path to entry")
    type: Literal["file", "directory", "symlink", "other"] = Field(
        ..., description="Type of directory entry"
    )
    permissions: str = Field(..., description="Permissions string")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    is_hidden: bool = Field(default=False, description="Whether entry is hidden")
    size: Optional[int] = Field(None, description="Size in bytes for files", ge=0)
    is_executable: bool = Field(
        default=False, description="Whether entry is executable"
    )
    symlink_target: Optional[str] = Field(
        None, description="Target if entry is symlink"
    )


class ModelLSToolResponse(BaseModel):
    """Structured response from LS (list) tool execution."""

    path: str = Field(..., description="Directory path that was listed")
    entries: List[ModelDirectoryEntry] = Field(
        ..., description="Directory entries found"
    )
    total_entries: int = Field(..., description="Total number of entries found", ge=0)
    directories_count: int = Field(..., description="Number of directories found", ge=0)
    files_count: int = Field(..., description="Number of files found", ge=0)
    permissions_accessible: bool = Field(
        ..., description="Whether directory was accessible"
    )
    hidden_entries_count: int = Field(
        default=0, description="Number of hidden entries found", ge=0
    )
    symlinks_count: int = Field(
        default=0, description="Number of symbolic links found", ge=0
    )
    ignore_patterns: Optional[List[str]] = Field(
        None, description="Ignore patterns that were applied"
    )
    recursive: bool = Field(default=False, description="Whether listing was recursive")
    execution_time_ms: Optional[int] = Field(
        None, description="Directory listing execution time", ge=0
    )
