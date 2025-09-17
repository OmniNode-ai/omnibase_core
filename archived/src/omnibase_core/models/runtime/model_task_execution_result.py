"""
Task Execution Result Model

ONEX-compliant models for task execution results, performance metrics,
and execution engine state management in the idle compute framework.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_onex_base_state import (
    ModelOnexInputState as OnexInputState,
)
from omnibase_core.models.core.model_onex_base_state import (
    OnexOutputState,
)
from omnibase_core.models.runtime.model_idle_compute_task import (
    EnumTaskStatus,
    ModelIdleComputeTask,
)


class EnumExecutorStatus(str, Enum):
    """Execution engine status."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    THROTTLING = "throttling"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class EnumExecutionStrategy(str, Enum):
    """Task execution strategies."""

    IMMEDIATE = "immediate"  # Execute as soon as resources available
    SCHEDULED = "scheduled"  # Execute at specific time
    RESOURCE_OPTIMAL = "resource_optimal"  # Wait for optimal resource conditions
    BATCH_OPTIMAL = "batch_optimal"  # Group with similar tasks


class ModelExecutionMetrics(BaseModel):
    """Detailed execution performance metrics."""

    cpu_usage_percent: list[float] = Field(
        default_factory=list,
        description="CPU usage samples during execution",
    )

    memory_usage_mb: list[float] = Field(
        default_factory=list,
        description="Memory usage samples during execution",
    )

    disk_io_mbps: list[float] = Field(
        default_factory=list,
        description="Disk I/O rate samples during execution",
    )

    network_io_mbps: list[float] = Field(
        default_factory=list,
        description="Network I/O rate samples during execution",
    )

    peak_cpu_usage: float = Field(
        default=0.0,
        description="Peak CPU usage during execution",
    )

    peak_memory_usage: float = Field(
        default=0.0,
        description="Peak memory usage during execution",
    )

    average_cpu_usage: float = Field(
        default=0.0,
        description="Average CPU usage during execution",
    )

    average_memory_usage: float = Field(
        default=0.0,
        description="Average memory usage during execution",
    )

    total_cpu_seconds: float = Field(
        default=0.0,
        description="Total CPU seconds consumed",
    )

    context_switches: int = Field(
        default=0,
        description="Number of context switches during execution",
    )

    page_faults: int = Field(
        default=0,
        description="Number of page faults during execution",
    )

    io_operations: int = Field(
        default=0,
        description="Number of I/O operations performed",
    )


class ModelTaskExecutionContext(BaseModel):
    """Execution context and environment for task."""

    executor_id: str = Field(description="ID of executor handling this task")

    worker_thread_id: str | None = Field(
        default=None,
        description="ID of worker thread executing task",
    )

    process_id: int | None = Field(
        default=None,
        description="Process ID if running in separate process",
    )

    execution_strategy: EnumExecutionStrategy = Field(
        description="Strategy used for execution",
    )

    resource_reservation_id: str | None = Field(
        default=None,
        description="ID of resource reservation for this task",
    )

    concurrency_group: str | None = Field(
        default=None,
        description="Group ID for parallel execution batching",
    )

    isolation_level: str = Field(
        default="thread",
        description="Isolation level (thread, process, container)",
    )

    timeout_seconds: float | None = Field(
        default=None,
        description="Execution timeout in seconds",
    )

    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables",
    )

    working_directory: str | None = Field(
        default=None,
        description="Working directory for task execution",
    )


class ModelAdvancedTaskExecutionResult(BaseModel):
    """Enhanced task execution result with comprehensive metrics."""

    task_id: str = Field(description="ID of executed task")

    execution_context: ModelTaskExecutionContext = Field(
        description="Execution context and environment",
    )

    status: EnumTaskStatus = Field(description="Final execution status")

    result: Any | None = Field(
        default=None,
        description="Task execution result data",
    )

    return_code: int | None = Field(
        default=None,
        description="Return code for process-based execution",
    )

    stdout: str | None = Field(
        default=None,
        description="Standard output captured during execution",
    )

    stderr: str | None = Field(
        default=None,
        description="Standard error captured during execution",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )

    exception_type: str | None = Field(
        default=None,
        description="Type of exception if one occurred",
    )

    exception_traceback: str | None = Field(
        default=None,
        description="Full exception traceback",
    )

    execution_duration: timedelta = Field(description="Total execution duration")

    queue_wait_time: timedelta = Field(
        description="Time spent waiting in queue before execution",
    )

    resource_acquisition_time: timedelta = Field(
        default=timedelta(0),
        description="Time spent acquiring resources",
    )

    metrics: ModelExecutionMetrics = Field(
        default_factory=ModelExecutionMetrics,
        description="Detailed performance metrics",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings during execution",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted")

    preemption_count: int = Field(
        default=0,
        description="Number of times task was preempted",
    )

    resource_efficiency_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Resource efficiency score (0-100)",
    )

    execution_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall execution quality score (0-100)",
    )

    started_at: datetime = Field(description="When execution started")

    completed_at: datetime = Field(description="When execution completed")

    checkpoints: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Execution checkpoints and milestones",
    )


class ModelExecutorState(BaseModel):
    """Current state of task execution engine."""

    executor_id: str = Field(description="Unique executor instance ID")

    status: EnumExecutorStatus = Field(description="Current executor status")

    max_concurrent_tasks: int = Field(
        ge=1,
        description="Maximum number of concurrent tasks",
    )

    current_task_count: int = Field(ge=0, description="Currently executing task count")

    total_tasks_executed: int = Field(
        ge=0,
        description="Total tasks executed since startup",
    )

    total_tasks_failed: int = Field(ge=0, description="Total tasks that failed")

    uptime: timedelta = Field(description="How long executor has been running")

    last_task_completion: datetime | None = Field(
        default=None,
        description="When last task completed",
    )

    resource_utilization: dict[str, float] = Field(
        default_factory=dict,
        description="Current resource utilization by executor",
    )

    performance_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Executor performance metrics",
    )

    worker_threads: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Information about worker threads",
    )

    error_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Recent error rate (0.0-1.0)",
    )

    throughput_tasks_per_minute: float = Field(
        default=0.0,
        ge=0.0,
        description="Current throughput in tasks per minute",
    )


class ModelExecutionEngineConfig(BaseModel):
    """Configuration for task execution engine."""

    max_concurrent_tasks: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum number of concurrent tasks",
    )

    max_concurrent_per_type: dict[str, int] = Field(
        default_factory=dict,
        description="Max concurrent tasks per task type",
    )

    enable_process_isolation: bool = Field(
        default=False,
        description="Whether to run tasks in separate processes",
    )

    enable_resource_monitoring: bool = Field(
        default=True,
        description="Whether to monitor resource usage during execution",
    )

    monitoring_interval_seconds: float = Field(
        default=1.0,
        gt=0.0,
        description="How often to sample resource metrics",
    )

    default_timeout_seconds: float | None = Field(
        default=3600.0,
        gt=0.0,
        description="Default task timeout in seconds",
    )

    retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Default number of retry attempts",
    )

    retry_delay_seconds: float = Field(
        default=1.0,
        gt=0.0,
        description="Delay between retry attempts",
    )

    enable_checkpointing: bool = Field(
        default=False,
        description="Whether to enable task checkpointing",
    )

    checkpoint_interval_seconds: float = Field(
        default=60.0,
        gt=0.0,
        description="Interval between checkpoints",
    )

    resource_limits: dict[str, float] = Field(
        default_factory=lambda: {
            "max_cpu_percent": 80.0,
            "max_memory_mb": 1024.0,
            "max_disk_io_mbps": 100.0,
        },
        description="Resource limits for task execution",
    )

    throttling_enabled: bool = Field(
        default=True,
        description="Whether to enable automatic throttling",
    )

    preemption_enabled: bool = Field(
        default=True,
        description="Whether to allow task preemption",
    )


class ModelExecutionEngineInputState(OnexInputState):
    """Input state for execution engine operations."""

    config: ModelExecutionEngineConfig = Field(
        default_factory=ModelExecutionEngineConfig,
        description="Execution engine configuration",
    )

    task: ModelIdleComputeTask | None = Field(
        default=None,
        description="Specific task to execute (if any)",
    )

    execution_strategy: EnumExecutionStrategy = Field(
        default=EnumExecutionStrategy.IMMEDIATE,
        description="How to execute the task",
    )

    override_resource_limits: bool = Field(
        default=False,
        description="Whether to override resource limits",
    )


class ModelExecutionEngineOutputState(OnexOutputState):
    """Output state for execution engine operations."""

    executor_state: ModelExecutorState = Field(
        description="Current state of execution engine",
    )

    execution_result: ModelAdvancedTaskExecutionResult | None = Field(
        default=None,
        description="Result of specific task execution",
    )

    active_tasks: list[str] = Field(
        default_factory=list,
        description="IDs of currently executing tasks",
    )

    performance_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Performance summary and statistics",
    )
