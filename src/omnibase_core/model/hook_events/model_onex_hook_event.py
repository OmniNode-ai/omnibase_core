"""ONEX Hook Event Model for Lifecycle Events.

This module provides a unified model for Claude Code lifecycle hook events that don't
involve direct tool execution but are critical for session tracking and workflow analysis.
These events include notifications, stop signals, user prompt submissions, and other
Claude Code session lifecycle events.

The model serves as the standardized ONEX representation for lifecycle events, designed
to capture the full context of Claude Code session state changes while maintaining
compatibility with Claude Code's dynamic payload structure.

Example Usage:
    >>> from model_onex_hook_event import ModelOnexHookEvent
    >>>
    >>> # User prompt submit event
    >>> user_event = ModelOnexHookEvent(
    ...     event_type="user-prompt-submit",
    ...     session_id="c121004e-97ea-432f-9dc6-b439aabcc24d",
    ...     timestamp="2023-08-15T20:00:00Z",
    ...     prompt="Please analyze this code for security vulnerabilities"
    ... )
    >>>
    >>> # Notification event
    >>> notification_event = ModelOnexHookEvent(
    ...     event_type="notification",
    ...     session_id="c121004e-97ea-432f-9dc6-b439aabcc24d",
    ...     timestamp="2023-08-15T20:01:00Z",
    ...     message="Analysis completed successfully",
    ...     content="Found 3 potential security issues"
    ... )
    >>>
    >>> # Stop event
    >>> stop_event = ModelOnexHookEvent(
    ...     event_type="stop",
    ...     session_id="c121004e-97ea-432f-9dc6-b439aabcc24d",
    ...     timestamp="2023-08-15T20:02:00Z",
    ...     stop_hook_active=True
    ... )

Technical Notes:
    - Handles multiple message field patterns (claude_message, message, content, prompt)
    - Maintains ONEX zero-tolerance policy by avoiding Any types
    - Uses Union types for timestamp flexibility (string or datetime)
    - Automatic timestamp validation converts datetime objects to ISO strings
    - Enables validate_assignment for runtime field validation
    - Uses `extra="allow"` to accommodate Claude Code's evolving payload structure

Event Types:
    - user-prompt-submit: User submitted a new prompt to Claude
    - notification: System or tool notifications
    - stop: Session stop signals
    - session-start: Session initialization events
    - subagent-stop: Sub-agent termination events
    - pre-compact: Pre-compaction lifecycle events
    - error: Error condition events

See Also:
    - ModelClaudeCodePreExecutionHookInput: For tool pre-execution events
    - ModelClaudeCodePostExecutionHookInput: For tool post-execution events
    - FactoryClaudeCodeEvent: For event processing and content extraction
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class ModelOnexHookEvent(BaseModel):
    """Lifecycle hook event model for Claude Code session events.

    This model represents standardized ONEX lifecycle events that capture Claude Code
    session state changes, user interactions, and system notifications. It provides
    a unified structure for events that don't involve direct tool execution but are
    essential for session tracking and workflow analysis.

    The model accommodates multiple message field patterns that Claude Code uses
    across different event types while maintaining strong typing and validation.

    Attributes:
        event_type: Type of lifecycle event (required)
        session_id: Claude session identifier for correlation (required)
        timestamp: Event occurrence time (required, auto-converted from datetime)
        tool_name: Associated tool name (optional, mainly for tool-adjacent events)
        claude_message: Claude's message content
        message: General message content
        content: Additional content data
        prompt: User prompt text (for user-prompt-submit events)
        transcript_path: Path to Claude Code transcript file
        cwd: Current working directory
        working_directory: Alternative working directory field
        hook_event_name: Claude Code's internal hook event name
        hook_type: Classification of hook type
        error: Error details if applicable
        topic: Topic or routing information
        stop_hook_active: Stop hook activation status (for stop events)
    """

    # Core event identification
    event_type: str = Field(..., description="Type of hook event")
    session_id: str = Field(..., description="Claude session identifier")
    timestamp: Union[str, datetime] = Field(..., description="Event timestamp")

    # Tool information (optional for lifecycle hooks)
    tool_name: Optional[str] = Field(
        None, description="Name of the tool (if applicable)"
    )

    # Claude Code specific fields
    claude_message: Optional[str] = Field(None, description="Claude message content")
    message: Optional[str] = Field(None, description="Message content")
    content: Optional[str] = Field(None, description="Content")
    prompt: Optional[str] = Field(
        None, description="User prompt (for user-prompt-submit)"
    )

    # Claude Code environment fields
    transcript_path: Optional[str] = Field(
        None, description="Path to Claude Code transcript"
    )
    cwd: Optional[str] = Field(None, description="Current working directory")
    working_directory: Optional[str] = Field(None, description="Working directory")
    hook_event_name: Optional[str] = Field(
        None, description="Claude Code hook event name"
    )
    hook_type: Optional[str] = Field(None, description="Hook type from Claude Code")

    # Additional context
    error: Optional[str] = Field(None, description="Error details")
    topic: Optional[str] = Field(None, description="Topic or routing info")
    stop_hook_active: Optional[bool] = Field(None, description="Stop hook status")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        """Convert datetime to string if needed."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        """Allow extra fields from Claude Code."""

        extra = "allow"  # Claude Code may send additional fields
        validate_assignment = True
