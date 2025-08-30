"""
System Data Model.

System information data structure.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelSystemData(BaseModel):
    """System information data."""

    # System identifiers
    system_id: Optional[str] = Field(None, description="System identifier")
    version: Optional[str] = Field(None, description="System version")
    environment: Optional[str] = Field(None, description="Environment name")

    # System metrics
    uptime_seconds: Optional[int] = Field(None, description="System uptime in seconds")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[int] = Field(None, description="Memory usage in MB")
    disk_usage_percent: Optional[float] = Field(
        None, description="Disk usage percentage"
    )

    # Configuration
    node_count: Optional[int] = Field(None, description="Number of active nodes")
    service_count: Optional[int] = Field(None, description="Number of active services")

    # Custom fields for extensibility
    custom_metrics: Optional[Dict[str, float]] = Field(
        None, description="Custom system metrics"
    )
    custom_info: Optional[Dict[str, str]] = Field(
        None, description="Custom system information"
    )
