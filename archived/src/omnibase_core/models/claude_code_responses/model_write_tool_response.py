# Generated from contract: tool_claude_code_response_models v1.0.0
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_operation_type import EnumOperationType


class ModelWriteToolResponse(BaseModel):
    """Structured response from Write tool execution."""

    file_path: str = Field(..., description="Path to the file that was written")
    bytes_written: int = Field(..., description="Number of bytes written to file", ge=0)
    lines_written: int = Field(..., description="Number of lines written to file", ge=0)
    file_existed: bool = Field(
        ...,
        description="Whether file existed before write operation",
    )
    encoding_used: str = Field(default="utf-8", description="Encoding used for writing")
    operation_type: EnumOperationType = Field(
        ...,
        description="Type of write operation performed",
    )
    backup_created: bool = Field(
        default=False,
        description="Whether backup was created before overwrite",
    )
    backup_path: str | None = Field(
        None,
        description="Path to backup file if created",
    )
    permissions_set: str | None = Field(
        None,
        description="File permissions set after write",
    )
