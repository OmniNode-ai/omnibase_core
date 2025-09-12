"""
Health Check Models for ONEX Runtime Services

Provides models for health monitoring and metrics reporting.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelHealthMetric(BaseModel):
    """Individual health metric."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Unit of measurement")
    threshold_warning: float | None = Field(None, description="Warning threshold")
    threshold_critical: float | None = Field(None, description="Critical threshold")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "queue_depth",
                "value": 150.0,
                "unit": "count",
                "threshold_warning": 1000.0,
                "threshold_critical": 5000.0,
            },
        },
    )


class ModelHealthCheck(BaseModel):
    """Health check result for a service or component."""

    status: EnumOnexStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Timestamp of health check")
    service_name: str = Field(..., description="Name of service/component checked")
    metrics: list[ModelHealthMetric] = Field(
        default_factory=list,
        description="Health metrics",
    )
    details: dict | None = Field(None, description="Additional health details")
    message: str | None = Field(None, description="Human-readable status message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "timestamp": "2024-01-01T12:00:00Z",
                "service_name": "task-queue",
                "metrics": [
                    {"name": "queue_depth", "value": 150.0, "unit": "count"},
                    {"name": "worker_count", "value": 4.0, "unit": "count"},
                ],
                "details": {"last_task_processed": "2024-01-01T11:59:00Z"},
                "message": "All systems operational",
            },
        },
    )
