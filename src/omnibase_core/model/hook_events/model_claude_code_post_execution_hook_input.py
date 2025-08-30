"""Claude Code post-execution hook input model.

This module provides input validation for raw data received from Claude Code's
post-execution hooks. It serves as the entry point for processing tool execution
responses after they complete, before being converted to standardized ONEX
tool execution events.

The model handles Claude Code's diverse response structures while maintaining
ONEX's strong typing requirements through strongly-typed response models that
replace loose Union types. Uses `extra="allow"` configuration to allow Claude Code
to send additional fields without validation errors.

Example Usage:
    >>> from model_claude_code_post_execution_hook_input import ModelClaudeCodePostExecutionHookInput
    >>>
    >>> # Minimal Claude Code response
    >>> hook_input = ModelClaudeCodePostExecutionHookInput(tool_name="Bash")
    >>> print(hook_input.tool_name)  # "Bash"
    >>>
    >>> # Complete Claude Code response
    >>> payload = {
    ...     "tool_name": "Bash",
    ...     "session_id": "c121004e-97ea-432f-9dc6-b439aabcc24d",
    ...     "tool_response": {
    ...         "stdout": "total 48\\ndrwxr-xr-x  12 user  staff   384 Aug 15 20:00 .\\n",
    ...         "stderr": "",
    ...         "exit_code": 0,
    ...         "interrupted": False
    ...     },
    ...     "duration_ms": 1250,
    ...     "cwd": "/Volumes/PRO-G40/Code/omnibase"
    ... }
    >>> hook_input = ModelClaudeCodePostExecutionHookInput(**payload)

Technical Notes:
    - Uses strongly-typed response models for Claude Code tool responses
    - Maintains ONEX zero-tolerance policy by avoiding Any types completely
    - All optional fields default to None for backward compatibility
    - Enables validate_assignment for runtime field validation
    - Duration measured in milliseconds for precise timing data
    - Replaces Union[str, int, float, bool, None, Dict[str, object], List[object]]

See Also:
    - ModelClaudeCodePreExecutionHookInput: For pre-execution hook validation
    - ModelToolPostExecutionEvent: Target ONEX event model for conversion
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.models.claude_code_responses import ClaudeCodeResponse


class ModelClaudeCodePostExecutionHookInput(BaseModel):
    """Raw input from Claude Code post-execution hooks.

    This model validates and structures post-execution data from Claude Code,
    including tool responses, execution timing, and any error information.
    The tool_response field uses strongly-typed models to accommodate different response
    structures from various Claude Code tools while maintaining complete type safety.

    Attributes:
        tool_name: Name of the executed tool (required)
        session_id: Claude session identifier for correlation
        tool_response: Tool execution response data (flexible structure)
        duration_ms: Execution duration in milliseconds
        claude_message: Claude's message content
        error: Error details if execution failed
        topic: Kafka topic or routing information
        working_directory: Execution working directory
        hook_type: Type of hook from Claude Code
        transcript_path: Path to Claude Code transcript
        cwd: Current working directory
        hook_event_name: Claude Code hook event name
    """

    # Core fields from Claude Code
    tool_name: str = Field(..., description="Name of the tool being executed")
    session_id: Optional[str] = Field(None, description="Claude session identifier")
    tool_response: Optional[ClaudeCodeResponse] = Field(
        None, description="Tool execution response"
    )
    duration_ms: Optional[int] = Field(
        None, description="Execution duration in milliseconds"
    )

    # Claude Code specific fields
    claude_message: Optional[str] = Field(None, description="Claude message content")
    error: Optional[str] = Field(None, description="Error details from Claude Code")
    topic: Optional[str] = Field(
        None, description="Kafka topic or similar routing info"
    )
    working_directory: Optional[str] = Field(None, description="Working directory path")
    hook_type: Optional[str] = Field(None, description="Hook type from Claude Code")

    # Additional Claude Code environment fields
    transcript_path: Optional[str] = Field(
        None, description="Path to Claude Code transcript"
    )
    cwd: Optional[str] = Field(None, description="Current working directory")
    hook_event_name: Optional[str] = Field(
        None, description="Claude Code hook event name"
    )

    class Config:
        """Allow extra fields from Claude Code."""

        extra = "allow"  # Claude Code may send additional fields
        validate_assignment = True
