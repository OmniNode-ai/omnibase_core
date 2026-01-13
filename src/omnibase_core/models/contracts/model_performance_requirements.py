"""
Performance Requirements Model.

Performance SLA specifications for contract-driven behavior providing:
- Measurable performance targets and resource constraints
- Runtime validation and optimization specifications
- Single operation and batch operation timing requirements
- Memory and CPU usage limits with validation

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceRequirements(BaseModel):
    """
    Performance SLA specifications for contract-driven behavior.

    Defines measurable performance targets and resource constraints
    for runtime validation and optimization.
    """

    single_operation_max_ms: int | None = Field(
        default=None,
        description="Maximum execution time for single operation in milliseconds",
        ge=1,
    )

    batch_operation_max_s: int | None = Field(
        default=None,
        description="Maximum execution time for batch operations in seconds",
        ge=1,
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
    )

    cpu_limit_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    throughput_min_ops_per_second: float | None = Field(
        default=None,
        description="Minimum throughput in operations per second",
        ge=0.0,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
