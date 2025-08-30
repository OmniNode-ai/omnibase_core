"""
Conversation Capture Models for OmniMemory Data Infrastructure

These models define the structure for storing complete conversation data
including user input, Claude responses, and conversation context for the
OmniMemory system's data infrastructure integration.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any


class EnumConversationRole(str, Enum):
    """Roles in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EnumMessageType(str, Enum):
    """Types of messages in conversation."""

    TEXT = "text"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"


@allow_dict_str_any("conversation data contains arbitrary structured content")
class ModelUserMessage(BaseModel):
    """Model for capturing user input messages."""

    id: str = Field(description="Unique identifier for the user message")
    conversation_id: str = Field(
        description="ID of the conversation this message belongs to",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the user message was sent",
    )
    content: str = Field(description="The user's message content")
    message_type: EnumMessageType = Field(
        default=EnumMessageType.TEXT,
        description="Type of message",
    )

    # Request metadata
    request_headers: dict[str, Any] = Field(
        default_factory=dict,
        description="HTTP headers from the request",
    )
    request_path: str = Field(default="", description="API path that was called")
    request_method: str = Field(default="POST", description="HTTP method used")

    # Context information
    model_requested: str | None = Field(
        None,
        description="AI model that was requested",
    )
    system_prompt: str | None = Field(
        None,
        description="System prompt sent with the request",
    )
    max_tokens: int | None = Field(None, description="Maximum tokens requested")
    temperature: float | None = Field(
        None,
        description="Temperature setting for the request",
    )

    # Full request data
    full_request_body: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete request body for analysis",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )


@allow_dict_str_any("Claude responses contain arbitrary structured content")
class ModelClaudeResponse(BaseModel):
    """Model for capturing Claude's responses."""

    id: str = Field(description="Unique identifier for Claude's response")
    conversation_id: str = Field(
        description="ID of the conversation this response belongs to",
    )
    user_message_id: str = Field(description="ID of the user message this responds to")

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When Claude's response was generated",
    )

    # Response content
    text_content: str | None = Field(
        None,
        description="Claude's text response before tool calls",
    )

    # Tool request information
    has_tool_requests: bool = Field(
        default=False,
        description="Whether this response contains tool requests",
    )
    tool_requests: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of tool requests made by Claude",
    )

    # Response metadata
    model_used: str | None = Field(
        None,
        description="AI model that generated this response",
    )
    stop_reason: str | None = Field(None, description="Why the response stopped")
    tokens_used: int | None = Field(
        None,
        description="Number of tokens used in the response",
    )

    # Full response data
    full_response_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete response data for analysis",
    )

    # Processing metadata
    response_time_ms: float | None = Field(
        None,
        description="Time taken to generate response in milliseconds",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )


class ModelConversationTurn(BaseModel):
    """Model linking user input to Claude response for conversation flow analysis."""

    id: str = Field(description="Unique identifier for this conversation turn")
    conversation_id: str = Field(description="ID of the conversation")
    turn_number: int = Field(
        description="Sequential number of this turn in conversation",
    )

    user_message_id: str = Field(description="ID of the user message")
    claude_response_id: str = Field(description="ID of Claude's response")

    # Turn analysis
    turn_successful: bool | None = Field(
        None,
        description="Whether this turn was successful (if determinable)",
    )
    user_satisfaction: str | None = Field(
        None,
        description="Indicators of user satisfaction with response",
    )

    # Context effectiveness
    context_injected: bool = Field(
        default=False,
        description="Whether OmniMemory context was injected for this turn",
    )
    rules_applied: list[str] = Field(
        default_factory=list,
        description="List of OmniMemory rules applied to this turn",
    )

    # Timing information
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this conversation turn started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When this conversation turn completed",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )


class ModelConversationSession(BaseModel):
    """Model for tracking complete conversation sessions."""

    id: str = Field(description="Unique identifier for the conversation session")

    # Session metadata
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the conversation session started",
    )
    last_activity_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the last activity occurred",
    )
    ended_at: datetime | None = Field(
        None,
        description="When the conversation session ended",
    )

    # Session statistics
    total_turns: int = Field(
        default=0,
        description="Total number of conversation turns",
    )
    total_tokens_used: int = Field(
        default=0,
        description="Total tokens used in this session",
    )
    total_tool_requests: int = Field(
        default=0,
        description="Total tool requests made in this session",
    )

    # Session context
    session_type: str = Field(
        default="claude_code",
        description="Type of conversation session",
    )
    user_agent: str | None = Field(None, description="User agent from requests")

    # OmniMemory integration
    omnimemory_rules_applied: int = Field(
        default=0,
        description="Number of OmniMemory rules applied in this session",
    )
    context_injection_count: int = Field(
        default=0,
        description="Number of times context was injected",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was last updated",
    )


@allow_dict_str_any("embedding data contains arbitrary vector and metadata content")
class ModelConversationEmbedding(BaseModel):
    """Model for storing conversation embeddings for semantic search."""

    id: str = Field(description="Unique identifier for this embedding")

    # Source reference
    source_type: str = Field(
        description="Type of source (user_message, claude_response, conversation_turn)",
    )
    source_id: str = Field(description="ID of the source record")
    conversation_id: str = Field(description="ID of the conversation")

    # Embedding data
    embedding_vector: list[float] = Field(
        description="Vector embedding generated by Ollama",
    )
    embedding_model: str = Field(
        default="mxbai-embed-large",
        description="Model used to generate the embedding",
    )
    embedding_dimensions: int = Field(
        description="Number of dimensions in the embedding vector",
    )

    # Content metadata
    content_hash: str = Field(description="Hash of the content that was embedded")
    content_type: str = Field(description="Type of content embedded")
    content_length: int = Field(description="Length of the content in characters")

    # Embedding metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this embedding was created",
    )
    embedding_time_ms: float | None = Field(
        None,
        description="Time taken to generate embedding in milliseconds",
    )
