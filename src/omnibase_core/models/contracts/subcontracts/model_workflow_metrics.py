"""
Workflow Metrics Model - ONEX Standards Compliant.

Model for performance metrics in workflow execution for the ONEX workflow coordination system.
"""

from pydantic import BaseModel, Field


class ModelWorkflowMetrics(BaseModel):
    """Performance metrics for workflow execution."""

    total_execution_time_ms: int = Field(
        ..., description="Total workflow execution time in milliseconds", ge=0
    )

    coordination_overhead_ms: int = Field(
        ..., description="Time spent on coordination overhead in milliseconds", ge=0
    )

    node_utilization_percent: float = Field(
        ..., description="Node utilization percentage", ge=0.0, le=100.0
    )

    parallelism_achieved: float = Field(
        ..., description="Achieved parallelism factor", ge=0.0
    )

    synchronization_delays_ms: int = Field(
        ..., description="Total time spent on synchronization delays", ge=0
    )

    resource_efficiency_score: float = Field(
        ..., description="Resource efficiency score", ge=0.0, le=1.0
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
