"""
Idle Compute Task Model

ONEX-compliant models for universal task registration, priority management,
and execution tracking in the idle compute framework.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator

from omnibase_core.model.core.model_onex_base_state import (
    ModelOnexInputState as OnexInputState,
)
from omnibase_core.model.core.model_onex_base_state import (
    OnexOutputState,
)
from omnibase_core.model.runtime.model_execution_stats import ModelExecutionStats
from omnibase_core.model.runtime.model_task_execution_context import (
    ModelTaskExecutionContext,
)
from omnibase_core.model.runtime.model_task_metadata import ModelTaskMetadata
from omnibase_core.model.runtime.model_task_performance_metrics import (
    ModelTaskPerformanceMetrics,
)


class EnumTaskPriority(str, Enum):
    """Task priority levels for scheduling."""

    CRITICAL = "critical"  # Must execute immediately, preempts other tasks
    HIGH = "high"  # Execute as soon as resources available
    MEDIUM = "medium"  # Execute during moderate system load
    LOW = "low"  # Execute only during idle periods
    BACKGROUND = "background"  # Execute when nothing else is pending


class EnumTaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"  # Waiting to be scheduled
    QUEUED = "queued"  # In priority queue, waiting for resources
    EXECUTING = "executing"  # Currently running
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed during execution
    CANCELLED = "cancelled"  # Cancelled before execution
    TIMEOUT = "timeout"  # Timed out during execution
    DEFERRED = "deferred"  # Deferred due to resource constraints


class EnumExecutionMode(str, Enum):
    """Task execution modes."""

    SERIAL = "serial"  # Execute one task at a time
    PARALLEL = "parallel"  # Can execute concurrently with others
    EXCLUSIVE = "exclusive"  # Must execute alone (no other tasks)
    COOPERATIVE = "cooperative"  # Shares resources cooperatively


class EnumTaskType(str, Enum):
    """Types of tasks that can be registered."""

    DOCUMENT_ANALYSIS = "document_analysis"
    DATA_PROCESSING = "data_processing"
    INDEX_BUILDING = "index_building"
    CLEANUP_OPERATION = "cleanup_operation"
    SYSTEM_MAINTENANCE = "system_maintenance"
    ML_TRAINING = "ml_training"
    BATCH_COMPUTATION = "batch_computation"
    CUSTOM = "custom"


class ModelResourceRequirements(BaseModel):
    """Resource requirements for task execution."""

    cpu_percent: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Required CPU percentage (0-100)",
    )

    memory_mb: float = Field(
        default=100.0,
        ge=0.0,
        description="Required memory in megabytes",
    )

    disk_io_mbps: float | None = Field(
        default=None,
        ge=0.0,
        description="Expected disk I/O in MB/s",
    )

    network_io_mbps: float | None = Field(
        default=None,
        ge=0.0,
        description="Expected network I/O in MB/s",
    )

    gpu_required: bool = Field(
        default=False,
        description="Whether GPU resources are required",
    )

    estimated_duration: timedelta | None = Field(
        default=None,
        description="Estimated execution duration",
    )

    max_duration: timedelta | None = Field(
        default=None,
        description="Maximum allowed execution duration",
    )


class ModelTaskExecution(BaseModel):
    """Task execution configuration and parameters."""

    function_name: str = Field(description="Name of function to execute")

    module_path: str = Field(description="Python module path containing the function")

    args: list[Any] = Field(
        default_factory=list,
        description="Positional arguments for function",
    )

    kwargs: str = Field(
        default="{}",
        description="JSON string of keyword arguments for function",
    )

    execution_context: "ModelTaskExecutionContext" = Field(
        default_factory=lambda: ModelTaskExecutionContext(),
        description="Execution context and metadata",
    )

    timeout_seconds: float | None = Field(
        default=None,
        gt=0.0,
        description="Execution timeout in seconds",
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Number of retry attempts on failure",
    )

    retry_delay_seconds: float = Field(
        default=1.0,
        gt=0.0,
        description="Delay between retry attempts",
    )


class ModelTaskDependencies(BaseModel):
    """Task dependencies and execution ordering."""

    depends_on: list[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on",
    )

    blocks: list[str] = Field(
        default_factory=list,
        description="List of task IDs this task blocks",
    )

    resource_conflicts: list[str] = Field(
        default_factory=list,
        description="List of task types that conflict with this task",
    )

    requires_exclusive_execution: bool = Field(
        default=False,
        description="Whether this task requires exclusive system access",
    )

    can_preempt: list[EnumTaskPriority] = Field(
        default_factory=list,
        description="Which priority levels this task can preempt",
    )


class ModelIdleComputeTask(BaseModel):
    """Complete task definition for idle compute framework."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier",
    )

    name: str = Field(description="Human-readable task name")

    description: str | None = Field(
        default=None,
        description="Detailed task description",
    )

    task_type: EnumTaskType = Field(description="Type of task for categorization")

    priority: EnumTaskPriority = Field(description="Task priority level")

    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.PARALLEL,
        description="How this task can be executed",
    )

    resource_requirements: ModelResourceRequirements = Field(
        default_factory=ModelResourceRequirements,
        description="Required system resources",
    )

    execution: ModelTaskExecution = Field(description="Execution configuration")

    dependencies: ModelTaskDependencies = Field(
        default_factory=ModelTaskDependencies,
        description="Task dependencies and conflicts",
    )

    status: EnumTaskStatus = Field(
        default=EnumTaskStatus.PENDING,
        description="Current task status",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When task was created",
    )

    scheduled_at: datetime | None = Field(
        default=None,
        description="When task was scheduled for execution",
    )

    started_at: datetime | None = Field(
        default=None,
        description="When task execution started",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When task execution completed",
    )

    submitter: str = Field(description="ID of process/service that submitted the task")

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for task categorization and filtering",
    )

    metadata: ModelTaskMetadata = Field(
        default_factory=ModelTaskMetadata,
        description="Additional task metadata",
    )

    result: Any | None = Field(default=None, description="Task execution result")

    error_message: str | None = Field(
        default=None,
        description="Error message if task failed",
    )

    execution_stats: ModelExecutionStats = Field(
        default_factory=ModelExecutionStats,
        description="Execution performance statistics",
    )

    @validator("scheduled_at")
    def scheduled_after_created(self, v, values):
        if v and "created_at" in values and v < values["created_at"]:
            msg = "scheduled_at must be after created_at"
            raise ValueError(msg)
        return v


class ModelTaskExecutionResult(BaseModel):
    """Result of task execution."""

    task_id: str = Field(description="ID of executed task")

    status: EnumTaskStatus = Field(description="Final execution status")

    result: Any | None = Field(default=None, description="Task execution result")

    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )

    execution_duration: timedelta = Field(description="How long task took to execute")

    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Actual resource usage during execution",
    )

    performance_metrics: ModelTaskPerformanceMetrics = Field(
        default_factory=ModelTaskPerformanceMetrics,
        description="Performance metrics and statistics",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings during execution",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted")


class ModelTaskQueueState(BaseModel):
    """Current state of task queues."""

    critical_queue_size: int = Field(ge=0)
    high_queue_size: int = Field(ge=0)
    medium_queue_size: int = Field(ge=0)
    low_queue_size: int = Field(ge=0)
    background_queue_size: int = Field(ge=0)

    total_pending_tasks: int = Field(ge=0)
    total_executing_tasks: int = Field(ge=0)
    total_completed_tasks: int = Field(ge=0)
    total_failed_tasks: int = Field(ge=0)

    queue_health_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall queue health score",
    )

    average_wait_time: timedelta = Field(description="Average time tasks wait in queue")

    processing_rate: float = Field(ge=0.0, description="Tasks processed per minute")

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ModelTaskRegistrationInputState(OnexInputState):
    """Input state for task registration operations."""

    task: ModelIdleComputeTask = Field(description="Task to register")

    immediate_execution: bool = Field(
        default=False,
        description="Whether to attempt immediate execution",
    )

    override_resource_checks: bool = Field(
        default=False,
        description="Whether to override resource availability checks",
    )


class ModelTaskRegistrationOutputState(OnexOutputState):
    """Output state for task registration operations."""

    task_id: str = Field(description="ID of registered task")

    queue_position: int | None = Field(
        default=None,
        description="Position in priority queue",
    )

    estimated_start_time: datetime | None = Field(
        default=None,
        description="Estimated execution start time",
    )

    registration_success: bool = Field(
        description="Whether registration was successful",
    )

    warning_messages: list[str] = Field(
        default_factory=list,
        description="Warning messages about registration",
    )

    queue_state: ModelTaskQueueState = Field(description="Current state of task queues")


class EnumTaskProviderStatus(str, Enum):
    """Task provider status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class ModelTaskProvider(BaseModel):
    """Model for task provider configuration and state."""

    provider_id: str = Field(description="Unique identifier for the task provider")

    provider_name: str = Field(description="Human-readable name for the provider")

    provider_type: str = Field(
        description="Type of provider (e.g., 'document_freshness', 'background_analysis')",
    )

    status: EnumTaskProviderStatus = Field(default=EnumTaskProviderStatus.ACTIVE)

    configuration: dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific configuration parameters",
    )

    priority: EnumTaskPriority = Field(
        default=EnumTaskPriority.LOW,
        description="Default priority for tasks from this provider",
    )

    max_concurrent_tasks: int = Field(
        default=1,
        ge=1,
        description="Maximum number of concurrent tasks from this provider",
    )

    resource_limits: ModelResourceRequirements = Field(
        description="Resource limits for tasks from this provider",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    last_task_submitted: datetime | None = Field(default=None)

    total_tasks_submitted: int = Field(default=0, ge=0)

    successful_tasks: int = Field(default=0, ge=0)

    failed_tasks: int = Field(default=0, ge=0)


# Rebuild models to resolve forward references
ModelTaskExecution.model_rebuild()
ModelIdleComputeTask.model_rebuild()
