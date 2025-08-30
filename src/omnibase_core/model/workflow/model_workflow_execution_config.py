"""Workflow execution configuration model with performance characteristics for distributed execution."""

from pydantic import BaseModel, Field, field_validator


class ModelWorkflowExecutionConfig(BaseModel):
    """
    Workflow execution configuration with performance characteristics and resource constraints.

    Supports distributed execution planning with metrics for speed, accuracy, cost, and load.
    """

    # Basic execution configuration
    mode_name: str = Field(..., description="Execution mode identifier", min_length=1)
    parallel_workers: int = Field(
        default=1,
        description="Number of parallel workers",
        ge=1,
        le=100,
    )
    priority_weight: float = Field(
        default=1.0,
        description="Execution priority weight",
        ge=0.1,
        le=10.0,
    )

    # Performance characteristics for distributed execution
    target_speed_factor: float | None = Field(
        None,
        description="Target execution speed factor (1.0 = baseline)",
        gt=0.0,
        le=10.0,
    )
    accuracy_requirement: float | None = Field(
        None,
        description="Required accuracy level (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    cost_budget_per_execution: float | None = Field(
        None,
        description="Cost budget per execution in credits",
        ge=0.0,
    )
    max_load_factor: float | None = Field(
        None,
        description="Maximum system load factor (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Resource constraints
    memory_limit_mb: int | None = Field(
        None,
        description="Memory limit in megabytes",
        gt=0,
        le=65536,  # 64GB max
    )
    cpu_limit_cores: float | None = Field(
        None,
        description="CPU core limit",
        gt=0.0,
        le=64.0,
    )
    timeout_seconds: int = Field(
        default=300,
        description="Execution timeout in seconds",
        gt=0,
        le=86400,  # 24 hours max
    )

    # Distributed execution features
    enable_retry: bool = Field(
        default=True,
        description="Enable automatic retry on failure",
    )
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum retry attempts",
        ge=0,
        le=10,
    )
    retry_backoff_strategy: str = Field(
        default="exponential",
        description="Retry backoff strategy",
    )
    enable_checkpointing: bool = Field(
        default=False,
        description="Enable execution checkpointing for long-running tasks",
    )
    checkpoint_interval_seconds: int | None = Field(
        None,
        description="Checkpoint interval in seconds",
        gt=0,
    )

    # Quality of service
    consistency_level: str = Field(
        default="eventual",
        description="Consistency level for distributed execution",
    )
    isolation_level: str = Field(
        default="read_committed",
        description="Transaction isolation level",
    )

    @field_validator("retry_backoff_strategy")
    @classmethod
    def validate_backoff_strategy(cls, v):
        """Validate retry backoff strategy."""
        valid_strategies = {"exponential", "linear", "fixed", "random"}
        if v not in valid_strategies:
            msg = f"retry_backoff_strategy must be one of {valid_strategies}"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("consistency_level")
    @classmethod
    def validate_consistency_level(cls, v):
        """Validate consistency level."""
        valid_levels = {"strong", "eventual", "session", "bounded_staleness"}
        if v not in valid_levels:
            msg = f"consistency_level must be one of {valid_levels}"
            raise ValueError(msg)
        return v

    @field_validator("checkpoint_interval_seconds")
    @classmethod
    def validate_checkpoint_interval(cls, v, info):
        """Ensure checkpoint interval is reasonable compared to timeout."""
        if v is not None and hasattr(info, "data") and "timeout_seconds" in info.data:
            if v >= info.data["timeout_seconds"]:
                msg = "checkpoint_interval_seconds must be less than timeout_seconds"
                raise ValueError(
                    msg,
                )
        return v
