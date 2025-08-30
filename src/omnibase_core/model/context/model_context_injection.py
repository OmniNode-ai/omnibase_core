"""
Context Injection Models for Claude Code Persistent Memory System.

These models define the structure for context injection data and responses
used in the automatic context enhancement system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EnumContextInjectionMode(str, Enum):
    """Enumeration for context injection modes."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    DISABLED = "disabled"


class EnumContextRelevance(str, Enum):
    """Enumeration for context relevance levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class model_HistoricalContext(BaseModel):
    """Model for historical context information."""

    conversation_id: str = Field(
        ..., description="Unique identifier for the conversation"
    )
    timestamp: datetime = Field(..., description="When the conversation occurred")
    user_message: str = Field(..., description="Original user message")
    assistant_response: str = Field(..., description="Assistant's response")
    tools_used: List[str] = Field(
        default_factory=list, description="Tools used in the conversation"
    )
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score to current request"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall relevance score"
    )
    success_outcome: bool = Field(
        ..., description="Whether the conversation was successful"
    )
    task_context: str = Field(..., description="Context of the task performed")


class model_ContextInjectionRequest(BaseModel):
    """Model for context injection requests."""

    user_request: str = Field(..., description="Current user request requiring context")
    session_id: Optional[str] = Field(None, description="Current session identifier")
    injection_mode: EnumContextInjectionMode = Field(
        default=EnumContextInjectionMode.AUTOMATIC,
        description="Mode for context injection",
    )
    max_context_items: int = Field(
        default=5, ge=1, le=20, description="Maximum number of context items"
    )
    relevance_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for context inclusion",
    )
    include_failed_attempts: bool = Field(
        default=False, description="Whether to include failed conversation attempts"
    )
    time_window_days: Optional[int] = Field(
        None, ge=1, le=365, description="Limit context to conversations within N days"
    )


class model_ContextInjectionResponse(BaseModel):
    """Model for context injection responses."""

    request_id: str = Field(
        ..., description="Unique identifier for this injection request"
    )
    user_request: str = Field(..., description="Original user request")
    extracted_keywords: List[str] = Field(
        default_factory=list, description="Keywords extracted from request"
    )
    intent_category: str = Field(..., description="Classified intent category")
    complexity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Request complexity score"
    )

    # Context matches
    historical_contexts: List[model_HistoricalContext] = Field(
        default_factory=list, description="Relevant historical conversations"
    )

    # Context summary
    context_summary: str = Field(..., description="Summary of injected context")
    relevance_level: EnumContextRelevance = Field(
        ..., description="Overall relevance level"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in context relevance"
    )

    # Injection details
    injection_mode: EnumContextInjectionMode = Field(
        ..., description="Mode used for injection"
    )
    context_items_found: int = Field(..., ge=0, description="Total context items found")
    context_items_injected: int = Field(
        ..., ge=0, description="Context items actually injected"
    )
    processing_time_ms: int = Field(
        ..., ge=0, description="Time taken to process injection"
    )

    # Enhanced prompt
    enhanced_context: Optional[str] = Field(
        None, description="Enhanced context for Claude's working memory"
    )

    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When injection was performed"
    )
    success: bool = Field(..., description="Whether context injection was successful")
    error_message: Optional[str] = Field(
        None, description="Error message if injection failed"
    )


class model_ContextEnhancementPrompt(BaseModel):
    """Model for context-enhanced prompts."""

    original_request: str = Field(..., description="Original user request")
    injected_context: str = Field(..., description="Injected historical context")
    enhanced_prompt: str = Field(..., description="Complete enhanced prompt for Claude")
    context_items_count: int = Field(
        ..., ge=0, description="Number of context items included"
    )
    enhancement_timestamp: datetime = Field(
        default_factory=datetime.now, description="When enhancement was applied"
    )


class model_ContextInjectionSettings(BaseModel):
    """Model for context injection system settings."""

    enabled: bool = Field(
        default=True, description="Whether context injection is enabled"
    )
    default_mode: EnumContextInjectionMode = Field(
        default=EnumContextInjectionMode.AUTOMATIC, description="Default injection mode"
    )
    max_context_items: int = Field(
        default=5, ge=1, le=20, description="Default maximum context items"
    )
    relevance_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Default relevance threshold"
    )
    similarity_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for context consideration",
    )
    time_window_days: int = Field(
        default=30, ge=1, le=365, description="Default time window for context searches"
    )

    # Performance settings
    max_processing_time_ms: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum time allowed for context processing",
    )
    cache_results: bool = Field(
        default=True, description="Whether to cache context results"
    )
    cache_ttl_seconds: int = Field(
        default=300, ge=60, le=3600, description="Cache time-to-live in seconds"
    )

    # Quality settings
    require_successful_outcomes: bool = Field(
        default=False, description="Only include contexts from successful conversations"
    )
    prioritize_recent: bool = Field(
        default=True, description="Give higher weight to recent conversations"
    )
    domain_specific_matching: bool = Field(
        default=True, description="Use domain-specific keyword matching"
    )


class model_ContextInjectionMetrics(BaseModel):
    """Model for context injection system metrics."""

    total_requests: int = Field(
        default=0, ge=0, description="Total injection requests processed"
    )
    successful_injections: int = Field(
        default=0, ge=0, description="Successful context injections"
    )
    failed_injections: int = Field(
        default=0, ge=0, description="Failed context injections"
    )

    # Performance metrics
    average_processing_time_ms: float = Field(
        default=0.0, ge=0.0, description="Average processing time"
    )
    max_processing_time_ms: int = Field(
        default=0, ge=0, description="Maximum processing time recorded"
    )
    min_processing_time_ms: int = Field(
        default=0, ge=0, description="Minimum processing time recorded"
    )

    # Quality metrics
    average_confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average confidence score"
    )
    average_context_items: float = Field(
        default=0.0, ge=0.0, description="Average context items injected"
    )

    # Usage metrics
    requests_by_mode: Dict[str, int] = Field(
        default_factory=dict, description="Request counts by injection mode"
    )
    requests_by_relevance: Dict[str, int] = Field(
        default_factory=dict, description="Request counts by relevance level"
    )

    # Timestamp
    last_updated: datetime = Field(
        default_factory=datetime.now, description="When metrics were last updated"
    )


class model_ContextCache(BaseModel):
    """Model for caching context analysis results."""

    cache_key: str = Field(..., description="Unique cache key")
    user_request_hash: str = Field(..., description="Hash of the user request")
    context_response: model_ContextInjectionResponse = Field(
        ..., description="Cached response"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When cache entry was created"
    )
    expires_at: datetime = Field(..., description="When cache entry expires")
    access_count: int = Field(
        default=1, ge=1, description="Number of times cache was accessed"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now, description="Last access timestamp"
    )
