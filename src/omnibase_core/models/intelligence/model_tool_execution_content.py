"""Tool execution content model for pattern learning.

Captures content from Claude Code tool executions for pattern extraction
and analytics in omniintelligence.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.hooks.claude_code import EnumClaudeCodeToolName


class ModelToolExecutionContent(BaseModel):
    """Content captured from Claude Code tool execution.

    Used by omniintelligence to extract code patterns from PostToolUse events.
    Implements dual-field pattern for forward compatibility with new tools.

    The dual-field pattern (tool_name_raw + tool_name) ensures:
    - Raw string preserved for debugging and forward compatibility
    - Enum provides type-safe classification and categorization
    - Unknown tools are captured with UNKNOWN enum value

    Privacy fields (is_content_redacted, redaction_policy_version) support
    configurable content redaction policies for sensitive data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Tool identification (dual-field pattern)
    tool_name_raw: str = Field(
        ...,
        min_length=1,
        description="Original tool name string from Claude Code",
    )
    tool_name: EnumClaudeCodeToolName = Field(
        ...,
        description="Classified tool name (UNKNOWN for unrecognized tools)",
    )

    # File context
    file_path: str | None = Field(
        default=None,
        description="File path if applicable",
    )
    language: str | None = Field(
        default=None,
        description="Detected programming language",
    )

    # Content capture (privacy-conscious)
    content_preview: str | None = Field(
        default=None,
        max_length=2000,
        description="Truncated content preview (max 2000 chars for pattern learning)",
    )
    content_length: int | None = Field(
        default=None,
        ge=0,
        description="Full content length in characters",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA256 hash of full content for deduplication",
    )

    # Privacy/redaction fields
    is_content_redacted: bool = Field(
        default=False,
        description="Whether content was redacted for privacy",
    )
    # string-version-ok: policy identifier, not semantic version
    redaction_policy_version: str | None = Field(
        default=None,
        description="Version of redaction policy applied (if redacted)",
    )

    # Execution metadata
    success: bool = Field(
        default=True,
        description="Whether tool execution succeeded",
    )
    error_type: str | None = Field(
        default=None,
        description="Error type if failed",
    )
    error_message: str | None = Field(
        default=None,
        max_length=500,
        description="Error message if failed",
    )
    duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Execution duration in milliseconds",
    )

    # Tracing
    # string-id-ok: Claude Code API provides string session identifiers
    session_id: str | None = Field(
        default=None,
        description="Claude Code session ID",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for tracing",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="Execution timestamp (from recorded session data)",
    )

    @classmethod
    def from_tool_name(
        cls,
        tool_name_raw: str,
        *,
        file_path: str | None = None,
        language: str | None = None,
        content_preview: str | None = None,
        content_length: int | None = None,
        content_hash: str | None = None,
        is_content_redacted: bool = False,
        # string-version-ok: policy identifier, not semantic version
        redaction_policy_version: str | None = None,
        success: bool = True,
        error_type: str | None = None,
        error_message: str | None = None,
        duration_ms: float | None = None,
        # string-id-ok: Claude Code API provides string session identifiers
        session_id: str | None = None,
        correlation_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> ModelToolExecutionContent:
        """Create instance from raw tool name with automatic enum resolution.

        This factory method prevents dual-field mismatches between tool_name_raw
        and tool_name by automatically resolving the enum from the raw string.
        Use this instead of the constructor when you have only the raw tool name.

        Args:
            tool_name_raw: Original tool name string from Claude Code.
            file_path: File path if applicable.
            language: Detected programming language.
            content_preview: Truncated content preview (max 2000 chars).
            content_length: Full content length in characters.
            content_hash: SHA256 hash of full content for deduplication.
            is_content_redacted: Whether content was redacted for privacy.
            redaction_policy_version: Version of redaction policy applied.
            success: Whether tool execution succeeded.
            error_type: Error type if failed.
            error_message: Error message if failed.
            duration_ms: Execution duration in milliseconds.
            session_id: Claude Code session ID.
            correlation_id: Correlation ID for tracing.
            timestamp: Execution timestamp.

        Returns:
            New ModelToolExecutionContent instance with consistent dual fields.

        Example:
            >>> content = ModelToolExecutionContent.from_tool_name(
            ...     "Read",
            ...     file_path="/path/to/file.py",
            ...     success=True,
            ... )
            >>> content.tool_name_raw
            'Read'
            >>> content.tool_name
            <EnumClaudeCodeToolName.READ: 'Read'>
        """
        return cls(
            tool_name_raw=tool_name_raw,
            tool_name=EnumClaudeCodeToolName.from_string(tool_name_raw),
            file_path=file_path,
            language=language,
            content_preview=content_preview,
            content_length=content_length,
            content_hash=content_hash,
            is_content_redacted=is_content_redacted,
            redaction_policy_version=redaction_policy_version,
            success=success,
            error_type=error_type,
            error_message=error_message,
            duration_ms=duration_ms,
            session_id=session_id,
            correlation_id=correlation_id,
            timestamp=timestamp,
        )


__all__ = ["ModelToolExecutionContent"]
