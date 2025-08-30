# Generated from contract: tool_claude_code_response_models v1.0.0
from typing import Optional

from pydantic import BaseModel, Field


class ModelBashToolResponse(BaseModel):
    """Structured response from Bash tool execution."""

    stdout: str = Field(..., description="Standard output from command execution")
    stderr: str = Field(..., description="Standard error output from command execution")
    exit_code: int = Field(
        ..., description="Exit code from command execution", ge=0, le=255
    )
    interrupted: bool = Field(
        default=False, description="Whether command execution was interrupted"
    )
    command: Optional[str] = Field(None, description="The command that was executed")
    working_directory: Optional[str] = Field(
        None, description="Working directory where command was executed"
    )
    timeout_occurred: bool = Field(
        default=False, description="Whether command timed out"
    )
    execution_time_ms: Optional[int] = Field(
        None, description="Actual execution time in milliseconds", ge=0
    )
