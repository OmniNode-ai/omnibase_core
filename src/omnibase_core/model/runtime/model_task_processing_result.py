"""
Task Processing Result Models

ONEX-compliant Pydantic models for task processing results.
Replaces Dict[str, Any] returns with strongly typed models.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# Use BaseModel directly until OnexBaseModel is available
OnexBaseModel = BaseModel


class ModelTaskExecutionResult(OnexBaseModel):
    """Result of task execution."""

    task_id: str = Field(..., description="ID of the executed task")
    status: str = Field(..., description="Execution status")
    execution_time: float = Field(..., description="Execution time in seconds")
    result: Optional[Dict] = Field(
        default=None, description="Task-specific result data"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    traceback: Optional[str] = Field(
        default=None, description="Error traceback if failed"
    )


class ModelDocumentAnalysisResult(OnexBaseModel):
    """Result of document freshness analysis."""

    document: str = Field(..., description="Document path")
    freshness_score: float = Field(..., description="Document freshness score")
    issues_found: int = Field(default=0, description="Number of issues found")
    recommendations: List[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )


class ModelBatchProcessingResult(OnexBaseModel):
    """Result of batch processing task."""

    total_items: int = Field(..., description="Total number of items")
    processed: int = Field(..., description="Number of items processed")
    batch_size: int = Field(..., description="Batch size used")
    status: str = Field(..., description="Processing status")
    failed_items: List[str] = Field(
        default_factory=list, description="IDs of failed items"
    )


class ModelCustomFunctionResult(OnexBaseModel):
    """Result of custom function execution."""

    function: str = Field(..., description="Function name executed")
    payload: Dict = Field(..., description="Input payload")
    result: str = Field(..., description="Function result")
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")


class ModelMaintenanceResult(OnexBaseModel):
    """Result of maintenance task."""

    deleted_count: int = Field(..., description="Number of items deleted")
    older_than_days: int = Field(..., description="Age threshold in days")
    executed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Execution timestamp"
    )
    additional_actions: Optional[List[str]] = Field(
        default=None, description="Other actions performed"
    )


class ModelResourceAnalysisResult(OnexBaseModel):
    """Result of resource analysis."""

    file_path: str = Field(..., description="Analyzed file path")
    file_name: str = Field(..., description="File name")
    file_size_bytes: int = Field(..., description="File size in bytes")
    last_modified: datetime = Field(..., description="Last modification time")
    age_days: int = Field(..., description="Age in days")
    content_hash: str = Field(..., description="Content hash")
    line_count: int = Field(..., description="Number of lines")
    word_count: int = Field(..., description="Number of words")
    freshness_status: str = Field(..., description="Freshness status")
    freshness_score: float = Field(..., description="Freshness score 0-1")
    todos_count: int = Field(default=0, description="Number of TODOs found")
    fixmes_count: int = Field(default=0, description="Number of FIXMEs found")
    has_title: bool = Field(..., description="Whether document has a title")
    has_code_blocks: bool = Field(..., description="Whether document has code blocks")
    has_links: bool = Field(..., description="Whether document has links")
    reading_time_minutes: int = Field(..., description="Estimated reading time")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    todos: List[str] = Field(default_factory=list, description="List of TODOs")
    fixmes: List[str] = Field(default_factory=list, description="List of FIXMEs")


class ModelTaskQueueStats(OnexBaseModel):
    """Task queue statistics."""

    total: int = Field(..., description="Total tasks")
    pending: int = Field(..., description="Pending tasks")
    running: int = Field(..., description="Running tasks")
    completed: int = Field(..., description="Completed tasks")
    failed: int = Field(..., description="Failed tasks")
    completed_today: int = Field(..., description="Tasks completed today")
    recent_tasks: List[Dict] = Field(
        default_factory=list, description="Recent task summaries"
    )
