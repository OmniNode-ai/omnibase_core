"""Claude Code pre-execution hook input model.

This module provides input validation for raw data received from Claude Code's
pre-execution hooks. It serves as the entry point for processing tool execution
requests before they are converted to standardized ONEX tool execution events.

The model is designed to handle Claude Code's dynamic payload structure while
maintaining ONEX's strong typing requirements through the use of `extra="allow"`
configuration, allowing Claude Code to send additional fields without validation errors.

Example Usage:
    >>> from model_claude_code_pre_execution_hook_input import ModelClaudeCodePreExecutionHookInput
    >>>
    >>> # Minimal Claude Code payload
    >>> hook_input = ModelClaudeCodePreExecutionHookInput(tool_name="Bash")
    >>> print(hook_input.tool_name)  # "Bash"
    >>>
    >>> # Complete Claude Code payload
    >>> payload = {
    ...     "tool_name": "Bash",
    ...     "session_id": "c121004e-97ea-432f-9dc6-b439aabcc24d",
    ...     "tool_input": '{"command": "git status"}',
    ...     "cwd": "/Volumes/PRO-G40/Code/omnibase",
    ...     "hook_event_name": "PreToolUse"
    ... }
    >>> hook_input = ModelClaudeCodePreExecutionHookInput(**payload)

Technical Notes:
    - Uses `extra="allow"` to accommodate Claude Code's evolving payload structure
    - Maintains ONEX zero-tolerance policy by avoiding Any types
    - All optional fields default to None for backward compatibility
    - Enables validate_assignment for runtime field validation

See Also:
    - ModelClaudeCodePostExecutionHookInput: For post-execution hook validation
    - ModelToolPreExecutionEvent: Target ONEX event model for conversion
"""

from typing import Dict, Optional, Union

from pydantic import BaseModel, Field


class ModelClaudeCodePreExecutionHookInput(BaseModel):
    """Raw input from Claude Code pre-execution hooks."""

    # Core fields from Claude Code
    tool_name: str = Field(..., description="Name of the tool being executed")
    session_id: Optional[str] = Field(None, description="Claude session identifier")
    tool_input: Optional[Union[str, Dict[str, Union[str, int, float, bool, None]]]] = (
        Field(None, description="Tool parameters as JSON string or dict")
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
