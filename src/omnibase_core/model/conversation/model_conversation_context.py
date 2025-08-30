"""
Models for conversation context and memory system.

These models provide strongly typed structures for capturing
and storing conversation context in the ONEX system.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelConversationInteraction(BaseModel):
    """Model for a single conversation interaction."""

    timestamp: datetime = Field(description="When the interaction occurred")
    user_message: str = Field(description="The user's message or request")
    assistant_response: str = Field(description="The assistant's response or action")
    tools_used: list[str] = Field(
        default_factory=list,
        description="List of tools used in this interaction",
    )
    outcome: str = Field(
        default="in_progress",
        description="Outcome of the interaction (completed, error, in_progress)",
    )
    task_context: str | None = Field(
        default=None,
        description="Optional context about the task type",
    )
    interaction_id: str = Field(description="Unique identifier for this interaction")


class ModelConversationMetadata(BaseModel):
    """Model for conversation metadata."""

    session_id: str = Field(description="Unique session identifier")
    session_start: datetime = Field(description="When the session started")
    interaction_count: int = Field(description="Number of interactions in session")
    task_type: str | None = Field(default=None, description="Type of task")
    domain: str | None = Field(default=None, description="Domain of the task")
    complexity: str | None = Field(default=None, description="Task complexity level")
    tools_count: int = Field(default=0, description="Total number of tools used")
    interaction_duration_ms: float = Field(
        default=0.0,
        description="Duration of the interaction in milliseconds",
    )


class ModelConversationBatch(BaseModel):
    """Model for a batch of conversation interactions."""

    conversation_batch: list[ModelConversationInteraction] = Field(
        description="List of conversation interactions",
    )
    batch_size: int = Field(description="Number of interactions in this batch")
    session_id: str = Field(description="Session ID for this batch")
    total_session_interactions: int = Field(
        description="Total interactions in the session",
    )
    flush_timestamp: datetime = Field(
        description="When this batch was flushed to storage",
    )


class ModelConversationSessionSummary(BaseModel):
    """Model for conversation session summary."""

    primary_task: str = Field(description="Primary task identified in the session")
    user_requests: str = Field(description="Summary of user requests")
    assistant_actions: str = Field(description="Summary of assistant actions")
    session_id: str = Field(description="Session identifier")
    total_interactions: int = Field(description="Total number of interactions")
    tools_used: list[str] = Field(
        default_factory=list,
        description="All tools used in the session",
    )
    outcome: str = Field(default="in_progress", description="Overall session outcome")


class ModelConversationCaptureResult(BaseModel):
    """Model for conversation capture result."""

    success: bool = Field(description="Whether the capture was successful")
    interaction_id: str | None = Field(
        default=None,
        description="ID of the captured interaction",
    )
    session_id: str | None = Field(default=None, description="Session ID")
    buffer_size: int = Field(default=0, description="Current buffer size")
    should_flush: bool = Field(
        default=False,
        description="Whether buffer should be flushed",
    )
    error: str | None = Field(
        default=None,
        description="Error message if capture failed",
    )
    message: str | None = Field(
        default=None,
        description="Additional status message",
    )


class ModelConversationFlushResult(BaseModel):
    """Model for conversation buffer flush result."""

    success: bool = Field(description="Whether the flush was successful")
    entry_id: str | None = Field(
        default=None,
        description="Debug entry ID if stored",
    )
    flushed_count: int = Field(default=0, description="Number of interactions flushed")
    session_id: str | None = Field(default=None, description="Session ID")
    error: str | None = Field(
        default=None,
        description="Error message if flush failed",
    )
    message: str | None = Field(
        default=None,
        description="Additional status message",
    )


class ModelConversationQueryResult(BaseModel):
    """Model for conversation memory query result."""

    success: bool = Field(description="Whether the query was successful")
    query: str = Field(description="The search query used")
    results_count: int = Field(default=0, description="Number of results found")
    results: list[ModelConversationInteraction] = Field(
        default_factory=list,
        description="List of matching conversation interactions",
    )
    error: str | None = Field(
        default=None,
        description="Error message if query failed",
    )


class ModelConversationSessionStatus(BaseModel):
    """Model for conversation session status."""

    session_id: str | None = Field(default=None, description="Current session ID")
    session_start: datetime | None = Field(
        default=None,
        description="When the session started",
    )
    total_interactions: int = Field(
        default=0,
        description="Total interactions in session",
    )
    buffer_size: int = Field(default=0, description="Current buffer size")
    buffer_limit: int = Field(
        default=5,
        description="Buffer size limit before auto-flush",
    )
    needs_flush: bool = Field(
        default=False,
        description="Whether buffer needs flushing",
    )
    capture_enabled: bool = Field(
        default=True,
        description="Whether capture is enabled",
    )


class ModelConversationMemoryStats(BaseModel):
    """Model for conversation memory statistics."""

    total_entries: int = Field(description="Total entries in memory")
    success_rate: float = Field(description="Success rate of stored interactions")
    recent_entries_7d: int = Field(description="Entries in last 7 days")
    current_session_interactions: int = Field(
        description="Interactions in current session",
    )
    buffer_size: int = Field(description="Current buffer size")
    knowledge_growth_rate: float = Field(description="Rate of knowledge base growth")
    database_status: str = Field(description="Database connection status")
    error: str | None = Field(
        default=None,
        description="Error message if stats retrieval failed",
    )


class ModelToolExecutionHook(BaseModel):
    """Model for tool execution hook data."""

    tool_name: str = Field(description="Name of the tool executed")
    tool_args: dict | None = Field(
        default=None,
        description="Arguments passed to the tool",
    )
    tool_result: str | None = Field(
        default=None,
        description="Result or outcome of the tool",
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Tool execution time in milliseconds",
    )
    success: bool = Field(
        default=True,
        description="Whether tool execution was successful",
    )


class ModelConversationHookStatus(BaseModel):
    """Model for conversation hook system status."""

    status: str = Field(description="Status of the hooks system")
    capture_enabled: bool = Field(description="Whether capture is enabled")
    session_id: str = Field(description="Current session ID")
    current_interaction_tools: int = Field(
        description="Number of tools in current interaction",
    )
    tools_in_current_interaction: list[str] = Field(
        default_factory=list,
        description="List of tools used in current interaction",
    )
    has_conversation_agent: bool = Field(
        description="Whether conversation agent is initialized",
    )
    message: str = Field(description="Status message")
