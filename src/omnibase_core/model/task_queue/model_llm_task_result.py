"""
LLM task result model for task queue completion tracking.

Extends the standard LLM response model with task execution metadata,
cost tracking, performance metrics, and error information for queue processing.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.database.models.model_task import EnumTaskStatus
from omnibase_core.model.llm.model_llm_response import ModelLLMResponse

from .model_task_configuration import (
    ModelLLMExecutionContext,
    ModelLLMStructuredOutput,
    ModelLLMTaskConfiguration,
)


class ModelLLMTaskResult(BaseModel):
    """
    LLM task result model for queue-based processing completion.

    Captures the complete execution result including LLM response,
    task metadata, performance metrics, cost tracking, and error
    information for monitoring and optimization.
    """

    # Task identification
    task_id: UUID = Field(description="Unique task identifier")

    task_name: str = Field(description="Human-readable task name", max_length=255)

    # Execution status
    status: EnumTaskStatus = Field(description="Final task execution status")

    # LLM response (if successful)
    llm_response: ModelLLMResponse | None = Field(
        default=None,
        description="LLM response data (None if task failed)",
    )

    # Timing information
    started_at: datetime = Field(description="When task execution began")

    completed_at: datetime = Field(description="When task execution finished")

    duration_seconds: float = Field(
        ge=0.0,
        description="Total execution time in seconds",
    )

    # Attempt tracking
    attempt_number: int = Field(
        ge=1,
        description="Which attempt this was (1 for first attempt)",
    )

    total_attempts: int = Field(ge=1, description="Total number of attempts made")

    # Provider and routing information
    provider_used: str | None = Field(
        default=None,
        description="LLM provider that handled the request",
    )

    model_used: str | None = Field(
        default=None,
        description="Specific model used for generation",
    )

    routing_decision: str | None = Field(
        default=None,
        description="Reason for provider/model selection",
    )

    failover_occurred: bool = Field(
        default=False,
        description="Whether failover to backup provider occurred",
    )

    failover_providers: list[str] = Field(
        default_factory=list,
        description="List of providers tried during failover",
    )

    # Cost and resource tracking
    total_cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Total cost incurred for this task",
    )

    cost_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by provider/model",
    )

    memory_used_mb: int | None = Field(
        default=None,
        description="Peak memory usage during execution",
    )

    gpu_used: bool = Field(default=False, description="Whether GPU was utilized")

    # Quality metrics
    output_quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Automated quality assessment score",
    )

    output_length_chars: int | None = Field(
        default=None,
        ge=0,
        description="Length of generated output in characters",
    )

    # Error information (if failed)
    error_message: str | None = Field(
        default=None,
        description="Error message if task failed",
    )

    error_code: str | None = Field(
        default=None,
        description="Structured error code for programmatic handling",
    )

    error_traceback: str | None = Field(
        default=None,
        description="Full error traceback for debugging",
    )

    # Configuration and context
    configuration_used: ModelLLMTaskConfiguration = Field(
        default_factory=ModelLLMTaskConfiguration,
        description="Actual configuration parameters used",
    )

    execution_context: ModelLLMExecutionContext = Field(
        default_factory=ModelLLMExecutionContext,
        description="Additional execution context and metadata",
    )

    # Output data
    structured_output: ModelLLMStructuredOutput | None = Field(
        default=None,
        description="Structured/parsed output data (if applicable)",
    )

    artifacts: list[str] = Field(
        default_factory=list,
        description="Paths to any generated artifacts or files",
    )

    # Callback tracking
    webhook_delivered: bool = Field(
        default=False,
        description="Whether webhook notification was delivered",
    )

    webhook_response_code: int | None = Field(
        default=None,
        description="HTTP response code from webhook delivery",
    )

    # Performance insights
    queue_wait_time_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Time spent waiting in queue before execution",
    )

    provider_latency_ms: int | None = Field(
        default=None,
        description="Provider-specific response latency",
    )

    tokens_per_second: float | None = Field(
        default=None,
        ge=0.0,
        description="Generation speed in tokens per second",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_name": "Document Analysis - Q4 Report",
                "status": "COMPLETED",
                "llm_response": {
                    "response": "Key insights from the Q4 report: Revenue increased 15%...",
                    "provider_used": "ollama",
                    "model_used": "mistral:7b",
                    "usage_metrics": {
                        "prompt_tokens": 1240,
                        "completion_tokens": 456,
                        "total_tokens": 1696,
                        "cost_usd": 0.0,
                        "latency_ms": 2340,
                    },
                    "finish_reason": "stop",
                    "confidence_score": 0.89,
                },
                "started_at": "2025-07-14T10:30:00Z",
                "completed_at": "2025-07-14T10:32:23Z",
                "duration_seconds": 143.2,
                "attempt_number": 1,
                "total_attempts": 1,
                "provider_used": "ollama",
                "model_used": "mistral:7b",
                "routing_decision": "local_preference_high_context",
                "failover_occurred": False,
                "total_cost_usd": 0.0,
                "cost_breakdown": {"ollama": 0.0},
                "memory_used_mb": 1840,
                "gpu_used": False,
                "output_quality_score": 0.91,
                "output_length_chars": 2567,
                "configuration_used": {
                    "analysis_depth": "comprehensive",
                    "output_format": "structured_json",
                    "document_id": "doc_12345",
                    "creativity_level": "balanced",
                    "tone": "technical",
                },
                "execution_context": {
                    "worker_id": "worker_001",
                    "worker_type": "dramatiq_llm_actor",
                    "queue_name": "llm_analysis",
                    "routing_decision": "local_preference_high_context",
                    "task_type": "llm_analysis",
                },
                "queue_wait_time_seconds": 12.5,
                "provider_latency_ms": 2340,
                "tokens_per_second": 3.2,
            },
        },
    )
