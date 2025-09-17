"""
Service Status Models for ONEX Runtime Services

Provides models for tracking service health, process information,
and operational status.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelProcessInfo(BaseModel):
    """Information about a running process."""

    pid: int = Field(..., description="Process ID")
    name: str = Field(..., description="Process name")
    status: str = Field(..., description="Process status (running, stopped, etc)")
    cpu_percent: float = Field(0.0, description="CPU usage percentage")
    memory_mb: float = Field(0.0, description="Memory usage in MB")
    uptime_seconds: float = Field(0.0, description="Process uptime in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pid": 12345,
                "name": "worker-default",
                "status": "running",
                "cpu_percent": 15.5,
                "memory_mb": 256.0,
                "uptime_seconds": 3600.0,
            },
        },
    )


class ModelServiceStatus(BaseModel):
    """Comprehensive service status information."""

    service_name: str = Field(..., description="Name of the service")
    status: EnumOnexStatus = Field(..., description="Overall service status")
    is_healthy: bool = Field(..., description="Whether service is healthy")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    last_check: datetime = Field(..., description="Timestamp of last health check")
    processes: list[ModelProcessInfo] = Field(
        default_factory=list,
        description="Running processes",
    )
    details: dict | None = Field(None, description="Additional status details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_name": "task-queue-service",
                "status": "success",
                "is_healthy": True,
                "uptime_seconds": 3600.0,
                "last_check": "2024-01-01T12:00:00Z",
                "processes": [
                    {
                        "pid": 12345,
                        "name": "queue-manager",
                        "status": "running",
                        "cpu_percent": 5.0,
                        "memory_mb": 128.0,
                        "uptime_seconds": 3600.0,
                    },
                ],
                "details": {"total_processes": 5, "health_issues": []},
            },
        },
    )
