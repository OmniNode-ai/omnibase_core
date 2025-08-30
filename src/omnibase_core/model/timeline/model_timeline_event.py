"""
Timeline Event Model

ONEX-compliant unified timeline event model supporting user messages,
tool executions, and Claude responses in chronological order.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_timeline_event_type import EnumTimelineEventType
from omnibase_core.model.core.model_node_metadata_block import \
    ModelNodeMetadataBlock


class ModelTimelineEvent(BaseModel):
    """
    Unified timeline event model for dashboard display.

    Supports three event types in Claude Code conversation flows:
    - USER_MESSAGE: User prompts with content and metadata
    - TOOL_EXECUTION: Tool calls with parameters, results, and performance metrics
    - CLAUDE_RESPONSE: Claude responses with content and timing information

    All events are timestamped and can be correlated through correlation_id.
    """

    # Core event identification
    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event identifier"
    )
    timestamp: datetime = Field(
        description="Event timestamp for chronological ordering"
    )
    event_type: EnumTimelineEventType = Field(description="Type of timeline event")
    session_id: str = Field(description="Claude Code session identifier")
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID linking related events (user request → tool → response)",
    )

    # User message data
    user_message: Optional[str] = Field(
        default=None, description="User message content for USER_MESSAGE events"
    )
    message_length: Optional[int] = Field(
        default=None, description="Character count of user message"
    )

    # Tool execution data
    tool_name: Optional[str] = Field(
        default=None, description="Tool name for TOOL_EXECUTION events"
    )
    tool_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool parameters as JSON object"
    )
    tool_result: Optional[str] = Field(
        default=None, description="Tool execution result or output"
    )
    tool_duration_ms: Optional[int] = Field(
        default=None, description="Tool execution duration in milliseconds"
    )
    tool_success: Optional[bool] = Field(
        default=None, description="Whether tool execution was successful"
    )

    # Claude response data
    response_text: Optional[str] = Field(
        default=None, description="Claude response content for CLAUDE_RESPONSE events"
    )
    token_count: Optional[int] = Field(
        default=None, description="Token count for Claude response"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Anthropic conversation identifier"
    )
    response_time_ms: Optional[int] = Field(
        default=None, description="Claude response generation time in milliseconds"
    )

    # Rich Metadata (claude-trace inspired)
    system_prompt: Optional[str] = Field(
        default=None, description="System prompt content for context tracking"
    )
    tool_definitions: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Available tool definitions at time of event"
    )
    claude_code_version: Optional[str] = Field(
        default=None, description="Claude Code version for behavior change tracking"
    )
    context_window_size: Optional[int] = Field(
        default=None, description="Context window size used for this event"
    )
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage at event time in MB"
    )

    # ONEX NodeMetadataBlock integration
    node_metadata: Optional[ModelNodeMetadataBlock] = Field(
        default=None, description="Rich ONEX metadata block for comprehensive context"
    )

    # Environment context
    environment_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Environment information (OS, Python version, etc.)"
    )

    # Performance metrics
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage at event time"
    )
    disk_usage_mb: Optional[float] = Field(default=None, description="Disk usage in MB")

    # User context
    user_preferences: Optional[Dict[str, Any]] = Field(
        default=None, description="User preferences and settings affecting behavior"
    )

    # Workflow metadata
    workflow_stage: Optional[str] = Field(
        default=None,
        description="Current workflow stage (planning, implementation, validation)",
    )
    active_personas: Optional[List[str]] = Field(
        default=None, description="List of active personas during this event"
    )
    mcp_servers_active: Optional[List[str]] = Field(
        default=None, description="List of active MCP servers during this event"
    )

    # Error context
    error_code: Optional[str] = Field(
        default=None, description="Error code if event represents an error"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if applicable"
    )
    stack_trace: Optional[str] = Field(
        default=None, description="Stack trace for debugging failures"
    )

    # Diff and versioning (claude-trace pattern)
    content_diff: Optional[Dict[str, Any]] = Field(
        default=None, description="Content differences from previous similar events"
    )
    version_changes: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Version changes in dependencies or tools"
    )

    # Custom metadata
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom metadata for specific use cases"
    )

    # Standard metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation timestamp"
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        # Strong typing enforcement
        validate_assignment = True
        use_enum_values = True

        # JSON serialization support
        json_encoders = {datetime: lambda v: v.isoformat()}

        # Schema generation
        schema_extra = {
            "examples": [
                {
                    "id": "msg_123e4567-e89b-12d3-a456-426614174000",
                    "timestamp": "2025-08-05T01:30:00.000Z",
                    "event_type": "USER_MESSAGE",
                    "session_id": "session_abc123",
                    "correlation_id": "conv_flow_001",
                    "user_message": "Read the README.md file and summarize it",
                    "message_length": 42,
                },
                {
                    "id": "tool_123e4567-e89b-12d3-a456-426614174001",
                    "timestamp": "2025-08-05T01:30:01.000Z",
                    "event_type": "TOOL_EXECUTION",
                    "session_id": "session_abc123",
                    "correlation_id": "conv_flow_001",
                    "tool_name": "Read",
                    "tool_parameters": {"file_path": "/README.md"},
                    "tool_result": "# Project Overview\\nThis is a...",
                    "tool_duration_ms": 250,
                    "tool_success": True,
                },
                {
                    "id": "resp_123e4567-e89b-12d3-a456-426614174002",
                    "timestamp": "2025-08-05T01:30:02.500Z",
                    "event_type": "CLAUDE_RESPONSE",
                    "session_id": "session_abc123",
                    "correlation_id": "conv_flow_001",
                    "response_text": "Based on the README.md file, this project...",
                    "token_count": 156,
                    "conversation_id": "conv_anthropic_xyz789",
                    "response_time_ms": 1500,
                },
            ]
        }

    def get_display_summary(self) -> str:
        """
        Get a brief summary for timeline display.

        Returns:
            str: Event summary appropriate for timeline UI
        """
        if self.event_type == EnumTimelineEventType.USER_MESSAGE:
            preview = (
                self.user_message[:50] + "..."
                if self.user_message and len(self.user_message) > 50
                else self.user_message
            )
            return f"📝 User: {preview}"

        elif self.event_type == EnumTimelineEventType.TOOL_EXECUTION:
            status = (
                "✅"
                if self.tool_success
                else "❌" if self.tool_success is False else "🔄"
            )
            duration = f" ({self.tool_duration_ms}ms)" if self.tool_duration_ms else ""
            return f"🔧 {status} {self.tool_name}{duration}"

        elif self.event_type == EnumTimelineEventType.CLAUDE_RESPONSE:
            preview = (
                self.response_text[:50] + "..."
                if self.response_text and len(self.response_text) > 50
                else self.response_text
            )
            tokens = f" ({self.token_count} tokens)" if self.token_count else ""
            return f"💬 Claude{tokens}: {preview}"

        return f"{self.event_type}: {self.id}"

    def is_correlated_with(self, other: "ModelTimelineEvent") -> bool:
        """
        Check if this event is correlated with another event.

        Args:
            other: Another timeline event to check correlation with

        Returns:
            bool: True if events are correlated via correlation_id
        """
        return (
            self.correlation_id is not None
            and other.correlation_id is not None
            and self.correlation_id == other.correlation_id
        )

    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Get a summary of rich metadata for debugging.

        Returns:
            Dict containing key metadata fields for analysis
        """
        return {
            "claude_code_version": self.claude_code_version,
            "active_personas": self.active_personas,
            "mcp_servers_active": self.mcp_servers_active,
            "workflow_stage": self.workflow_stage,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "context_window_size": self.context_window_size,
            "has_system_prompt": bool(self.system_prompt),
            "has_tool_definitions": bool(self.tool_definitions),
            "has_node_metadata": bool(self.node_metadata),
            "has_error": bool(self.error_code or self.error_message),
        }

    def get_performance_metrics(self) -> Dict[str, Optional[float]]:
        """
        Extract performance metrics for analysis.

        Returns:
            Dict with performance-related metrics
        """
        return {
            "tool_duration_ms": (
                float(self.tool_duration_ms) if self.tool_duration_ms else None
            ),
            "response_time_ms": (
                float(self.response_time_ms) if self.response_time_ms else None
            ),
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_usage_mb": self.disk_usage_mb,
            "token_count": float(self.token_count) if self.token_count else None,
            "message_length": (
                float(self.message_length) if self.message_length else None
            ),
        }

    def has_version_changes(self) -> bool:
        """
        Check if event includes version change information.

        Returns:
            True if version changes are tracked
        """
        return bool(self.version_changes and len(self.version_changes) > 0)

    def get_tool_context(self) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive tool execution context.

        Returns:
            Dict with tool context or None if not a tool event
        """
        if self.event_type != EnumTimelineEventType.TOOL_EXECUTION:
            return None

        return {
            "tool_name": self.tool_name,
            "parameters": self.tool_parameters,
            "success": self.tool_success,
            "duration_ms": self.tool_duration_ms,
            "result_preview": (
                self.tool_result[:200] + "..."
                if self.tool_result and len(self.tool_result) > 200
                else self.tool_result
            ),
            "environment": self.environment_info,
            "active_personas": self.active_personas,
            "mcp_servers": self.mcp_servers_active,
        }
