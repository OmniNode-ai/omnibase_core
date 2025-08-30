"""
Context data models for OmniMemory system.

Represents context data and evaluation context for rule processing.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelFrameworkContext(BaseModel):
    """Framework-specific context information."""

    framework_name: str = Field(..., description="Name of the framework")
    framework_version: Optional[str] = Field(None, description="Framework version")
    configuration_path: Optional[str] = Field(
        None, description="Configuration file path"
    )
    additional_info: Optional[str] = Field(
        None, description="Additional framework information"
    )


class ModelToolUsageMetrics(BaseModel):
    """Tool usage metrics and statistics."""

    tool_name: str = Field(..., description="Name of the tool")
    usage_count: int = Field(default=0, description="Number of times used")
    success_rate: float = Field(default=0.0, description="Success rate percentage")
    average_execution_time_ms: float = Field(
        default=0.0, description="Average execution time"
    )
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")


class ModelPerformanceMetric(BaseModel):
    """Individual performance metric."""

    metric_name: str = Field(..., description="Name of the metric")
    metric_value: float = Field(..., description="Numeric value of the metric")
    metric_unit: Optional[str] = Field(None, description="Unit of measurement")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Measurement timestamp"
    )


class ModelContextData(BaseModel):
    """Represents structured context data for rule evaluation."""

    conversation_id: Optional[str] = Field(
        None, description="Unique conversation identifier"
    )
    user_intent: Optional[str] = Field(None, description="Detected user intent")
    current_task: Optional[str] = Field(
        None, description="Current task being performed"
    )
    project_path: Optional[str] = Field(None, description="Current project path")
    file_patterns: List[str] = Field(
        default_factory=list, description="File patterns in context"
    )
    coding_patterns: List[str] = Field(
        default_factory=list, description="Detected coding patterns"
    )
    error_patterns: List[str] = Field(
        default_factory=list, description="Error patterns detected"
    )
    framework_contexts: List[ModelFrameworkContext] = Field(
        default_factory=list, description="Framework-specific contexts"
    )
    tool_usage_metrics: List[ModelToolUsageMetrics] = Field(
        default_factory=list, description="Tool usage metrics"
    )
    performance_metrics: List[ModelPerformanceMetric] = Field(
        default_factory=list, description="Performance metrics"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Context creation timestamp"
    )


class ModelEvaluationMetadata(BaseModel):
    """Metadata for the evaluation process."""

    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    evaluation_type: str = Field(..., description="Type of evaluation")
    start_time: datetime = Field(
        default_factory=datetime.utcnow, description="Evaluation start time"
    )
    end_time: Optional[datetime] = Field(None, description="Evaluation end time")
    success: bool = Field(default=False, description="Whether evaluation succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata_values: List[str] = Field(
        default_factory=list, description="Additional metadata values"
    )


class ModelPatternMatch(BaseModel):
    """Represents a pattern match result."""

    pattern_name: str = Field(..., description="Name of the pattern")
    pattern_type: str = Field(..., description="Type of pattern")
    match_location: Optional[str] = Field(
        None, description="Where the pattern was found"
    )
    confidence_score: float = Field(..., description="Confidence score of the match")


class ModelRuleEvaluationContext(BaseModel):
    """Represents context for rule evaluation operations."""

    context_data: ModelContextData = Field(..., description="Structured context data")
    evaluation_metadata: ModelEvaluationMetadata = Field(
        ..., description="Evaluation process metadata"
    )
    matched_patterns: List[ModelPatternMatch] = Field(
        default_factory=list, description="Patterns that matched"
    )
    token_budget: Optional[int] = Field(None, description="Available token budget")
    priority_hints: List[str] = Field(
        default_factory=list, description="Priority hints for rule processing"
    )
