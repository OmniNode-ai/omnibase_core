"""
LLM task request model for task queue integration.

Extends the standard LLM request model with task-specific metadata,
scheduling information, and resource requirements for queue processing.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.database.models.model_task import EnumTaskPriority
from omnibase_core.enums.enum_task_types import EnumTaskType
from omnibase_core.models.llm.model_llm_request import ModelLLMRequest

from .model_task_configuration import ModelLLMTaskConfiguration


class ModelLLMTaskRequest(BaseModel):
    """
    LLM task request model for queue-based processing.

    Combines standard LLM request parameters with task queue metadata,
    scheduling requirements, and resource constraints for intelligent
    routing and execution planning.
    """

    # Core LLM request
    llm_request: ModelLLMRequest = Field(
        description="Standard LLM request with prompt and generation parameters",
    )

    # Task metadata
    task_name: str = Field(
        description="Human-readable task name for tracking",
        max_length=255,
    )

    task_type: EnumTaskType = Field(description="Type of LLM task being requested")

    priority: EnumTaskPriority = Field(
        default=EnumTaskPriority.MEDIUM,
        description="Task priority for queue processing",
    )

    # Scheduling
    scheduled_at: datetime | None = Field(
        default=None,
        description="When to execute the task (immediate if None)",
    )

    expires_at: datetime | None = Field(
        default=None,
        description="Task expiration time",
    )

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts if task fails",
    )

    # Resource requirements
    estimated_duration_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Estimated execution time in seconds",
    )

    estimated_memory_mb: int | None = Field(
        default=None,
        ge=100,
        description="Estimated memory requirement in MB",
    )

    requires_gpu: bool = Field(
        default=False,
        description="Whether task requires GPU acceleration",
    )

    # Cost management
    max_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum allowed cost in USD for this task",
    )

    cost_preference: str = Field(
        default="balanced",
        description="Cost preference: 'cheapest', 'balanced', 'fastest'",
    )

    # Privacy and routing
    require_local_execution: bool = Field(
        default=False,
        description="Force execution on local models only (no API calls)",
    )

    exclude_providers: list[str] = Field(
        default_factory=list,
        description="Provider names to exclude from routing",
    )

    # Context and tracking
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for tracking related tasks",
    )

    parent_task_id: UUID | None = Field(
        default=None,
        description="Parent task ID for dependency tracking",
    )

    submitted_by: str | None = Field(
        default=None,
        description="User or system that submitted the task",
    )

    source_system: str = Field(
        default="api",
        description="Source system (api, cli, scheduler, etc.)",
    )

    # Additional configuration
    configuration: ModelLLMTaskConfiguration = Field(
        default_factory=ModelLLMTaskConfiguration,
        description="Task-specific configuration parameters",
    )

    # Callback configuration
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL to call when task completes",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "llm_request": {
                    "prompt": "Analyze this document for key insights and themes",
                    "system_prompt": "You are an expert document analyst",
                    "model_requirements": {
                        "min_context_length": 8192,
                        "capabilities": ["text_analysis", "summarization"],
                        "max_cost_per_token": 0.002,
                    },
                    "generation_params": {"temperature": 0.3, "max_tokens": 2000},
                    "provider_preferences": ["ollama", "openai"],
                },
                "task_name": "Document Analysis - Q4 Report",
                "task_type": "llm_analysis",
                "priority": "HIGH",
                "max_attempts": 2,
                "estimated_duration_seconds": 120,
                "estimated_memory_mb": 2048,
                "requires_gpu": False,
                "max_cost_usd": 0.50,
                "cost_preference": "balanced",
                "require_local_execution": False,
                "submitted_by": "document_freshness_worker",
                "source_system": "scheduler",
                "configuration": {
                    "document_id": "doc_12345",
                    "analysis_type": "quarterly_insights",
                    "output_format": "structured_json",
                },
            },
        },
    )
