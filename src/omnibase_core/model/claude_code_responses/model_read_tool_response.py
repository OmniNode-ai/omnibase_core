# Generated from contract: tool_claude_code_response_models v1.0.0
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelFileMetadata(BaseModel):
    """File metadata information."""

    last_modified: datetime = Field(..., description="Last modification timestamp")
    permissions: str = Field(..., description="File permissions string")
    is_executable: bool = Field(default=False, description="Whether file is executable")
    is_symlink: bool = Field(
        default=False, description="Whether file is a symbolic link"
    )
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    owner: Optional[str] = Field(None, description="File owner")
    group: Optional[str] = Field(None, description="File group")
    symlink_target: Optional[str] = Field(
        None, description="Target of symbolic link if applicable"
    )


class ModelReadToolResponse(BaseModel):
    """Structured response from Read tool execution."""

    content: str = Field(..., description="File content that was read")
    file_path: str = Field(..., description="Path to the file that was read")
    lines_read: int = Field(..., description="Number of lines read from file", ge=0)
    file_size_bytes: int = Field(
        ..., description="Total size of the file in bytes", ge=0
    )
    encoding: str = Field(default="utf-8", description="File encoding detected")
    is_binary: bool = Field(
        default=False, description="Whether file is detected as binary"
    )
    line_offset: Optional[int] = Field(
        None, description="Starting line number if offset was used", ge=1
    )
    line_limit: Optional[int] = Field(
        None, description="Maximum lines read if limit was applied", ge=1
    )
    truncated: bool = Field(
        default=False, description="Whether content was truncated due to size limits"
    )
    metadata: Optional[ModelFileMetadata] = Field(
        None, description="Additional file metadata"
    )
