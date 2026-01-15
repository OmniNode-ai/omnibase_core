"""
Load Metrics Model

Load metrics for node instances including queue depth, throughput,
and capacity utilization.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelLoadMetrics(BaseModel):
    """
    Load metrics for node instances.

    This model tracks load-related metrics including queue depth,
    throughput, capacity utilization, and saturation indicators.
    """

    queue_depth: int = Field(default=0, description="Current queue depth", ge=0)

    max_queue_depth: int = Field(default=1000, description="Maximum queue depth", ge=1)

    throughput_per_second: float = Field(
        default=0.0,
        description="Current throughput per second",
        ge=0.0,
    )

    capacity_utilization: float = Field(
        default=0.0,
        description="Capacity utilization percentage",
        ge=0.0,
        le=100.0,
    )

    active_tasks: int = Field(default=0, description="Number of active tasks", ge=0)

    max_concurrent_tasks: int = Field(
        default=100,
        description="Maximum concurrent tasks",
        ge=1,
    )

    pending_tasks: int = Field(default=0, description="Number of pending tasks", ge=0)

    completed_tasks_total: int = Field(
        default=0,
        description="Total completed tasks",
        ge=0,
    )

    failed_tasks_total: int = Field(default=0, description="Total failed tasks", ge=0)

    average_task_duration_ms: float = Field(
        default=0.0,
        description="Average task duration in milliseconds",
        ge=0.0,
    )

    p95_task_duration_ms: float | None = Field(
        default=None,
        description="95th percentile task duration",
        ge=0.0,
    )

    p99_task_duration_ms: float | None = Field(
        default=None,
        description="99th percentile task duration",
        ge=0.0,
    )

    rejection_rate: float = Field(
        default=0.0,
        description="Rejection rate percentage",
        ge=0.0,
        le=100.0,
    )

    saturation_score: float = Field(
        default=0.0,
        description="Saturation score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    last_overload_timestamp: datetime | None = Field(
        default=None,
        description="Last time node was overloaded",
    )

    custom_load_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Custom load metrics",
    )

    def is_overloaded(self, threshold: float = 0.8) -> bool:
        """
        Check if node is overloaded.

        Args:
            threshold: Saturation threshold for overload

        Returns:
            True if node is overloaded
        """
        return (
            self.saturation_score >= threshold
            or self.capacity_utilization >= 90.0
            or self.queue_depth >= (self.max_queue_depth * 0.9)
            or self.rejection_rate >= 10.0
        )

    def get_load_score(self) -> float:
        """
        Calculate load score (0.0 to 1.0).

        Returns:
            Load score where 0.0 is no load and 1.0 is fully loaded
        """
        # Calculate various load factors
        queue_factor = self.queue_depth / max(1, self.max_queue_depth)
        task_factor = self.active_tasks / max(1, self.max_concurrent_tasks)
        capacity_factor = self.capacity_utilization / 100.0

        # Weight the factors
        weights = {"queue": 0.3, "tasks": 0.3, "capacity": 0.2, "saturation": 0.2}

        score = (
            queue_factor * weights["queue"]
            + task_factor * weights["tasks"]
            + capacity_factor * weights["capacity"]
            + self.saturation_score * weights["saturation"]
        )

        return max(0.0, min(1.0, score))

    def can_accept_load(self, additional_load: int = 1) -> bool:
        """
        Check if node can accept additional load.

        Args:
            additional_load: Number of additional tasks

        Returns:
            True if node can accept the load
        """
        if self.is_overloaded():
            return False

        future_queue = self.queue_depth + additional_load
        future_tasks = self.active_tasks + additional_load

        return (
            future_queue < self.max_queue_depth
            and future_tasks < self.max_concurrent_tasks
            and self.rejection_rate < 5.0
        )

    def update_saturation(self) -> None:
        """Update saturation score based on current metrics."""
        # Simple saturation calculation
        queue_saturation = self.queue_depth / max(1, self.max_queue_depth)
        task_saturation = self.active_tasks / max(1, self.max_concurrent_tasks)
        capacity_saturation = self.capacity_utilization / 100.0

        # Take the maximum as saturation indicator
        self.saturation_score = max(
            queue_saturation,
            task_saturation,
            capacity_saturation,
        )
