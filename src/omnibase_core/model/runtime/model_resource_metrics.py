"""
Resource Metrics Model

ONEX-compliant model for real-time system resource monitoring and threshold management.
Provides strongly-typed interfaces for CPU, memory, disk I/O, and composite resource metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator

from omnibase_core.model.core.model_onex_base_state import (
    ModelOnexInputState as OnexInputState,
)
from omnibase_core.model.core.model_onex_base_state import (
    OnexOutputState,
)


class EnumResourceType(str, Enum):
    """Resource types for monitoring."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    GPU = "gpu"
    COMPOSITE = "composite"


class EnumResourceStatus(str, Enum):
    """Resource utilization status levels."""

    IDLE = "idle"  # < 30% utilization
    LOW = "low"  # 30-50% utilization
    MODERATE = "moderate"  # 50-70% utilization
    HIGH = "high"  # 70-85% utilization
    CRITICAL = "critical"  # 85-95% utilization
    SATURATED = "saturated"  # > 95% utilization


class EnumThresholdType(str, Enum):
    """Threshold types for resource monitoring."""

    IDLE_THRESHOLD = "idle_threshold"
    PROCESSING_THRESHOLD = "processing_threshold"
    THROTTLE_THRESHOLD = "throttle_threshold"
    CRITICAL_THRESHOLD = "critical_threshold"


class ModelResourceThresholds(BaseModel):
    """Resource utilization thresholds for different processing modes."""

    idle_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Below this threshold, system is considered idle (default: 30%)",
    )

    processing_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Above this threshold, reduce processing intensity (default: 70%)",
    )

    throttle_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Above this threshold, throttle processing aggressively (default: 85%)",
    )

    critical_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Above this threshold, stop all non-critical processing (default: 95%)",
    )

    @validator("processing_threshold")
    def processing_gt_idle(self, v, values):
        if "idle_threshold" in values and v <= values["idle_threshold"]:
            msg = "processing_threshold must be greater than idle_threshold"
            raise ValueError(msg)
        return v

    @validator("throttle_threshold")
    def throttle_gt_processing(self, v, values):
        if "processing_threshold" in values and v <= values["processing_threshold"]:
            msg = "throttle_threshold must be greater than processing_threshold"
            raise ValueError(
                msg,
            )
        return v

    @validator("critical_threshold")
    def critical_gt_throttle(self, v, values):
        if "throttle_threshold" in values and v <= values["throttle_threshold"]:
            msg = "critical_threshold must be greater than throttle_threshold"
            raise ValueError(
                msg,
            )
        return v


class ModelResourceSnapshot(BaseModel):
    """Single point-in-time resource measurement."""

    resource_type: EnumResourceType
    utilization_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="Resource utilization as percentage (0-100)",
    )
    available_amount: float | None = Field(
        default=None,
        description="Available resource amount in appropriate units",
    )
    total_amount: float | None = Field(
        default=None,
        description="Total resource amount in appropriate units",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this measurement was taken",
    )
    status: EnumResourceStatus = Field(
        description="Computed status based on utilization",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional resource-specific metadata",
    )


class ModelSystemResourceMetrics(BaseModel):
    """Comprehensive system resource metrics snapshot."""

    cpu: ModelResourceSnapshot = Field(description="CPU utilization metrics")
    memory: ModelResourceSnapshot = Field(description="Memory utilization metrics")
    disk_io: ModelResourceSnapshot = Field(description="Disk I/O utilization metrics")
    network_io: ModelResourceSnapshot | None = Field(
        default=None,
        description="Network I/O utilization metrics",
    )
    gpu: ModelResourceSnapshot | None = Field(
        default=None,
        description="GPU utilization metrics if available",
    )

    composite_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Weighted composite resource utilization score",
    )
    composite_status: EnumResourceStatus = Field(
        description="Overall system resource status",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this metrics snapshot was collected",
    )

    thresholds: ModelResourceThresholds = Field(
        default_factory=ModelResourceThresholds,
        description="Thresholds used for status computation",
    )

    is_idle_capable: bool = Field(
        description="Whether system can handle idle compute tasks",
    )
    suggested_concurrency: int = Field(
        ge=0,
        description="Suggested number of concurrent tasks based on current load",
    )


class ModelResourceMonitorConfig(BaseModel):
    """Configuration for resource monitoring system."""

    monitoring_interval_seconds: float = Field(
        default=5.0,
        gt=0.0,
        description="How often to collect resource metrics",
    )

    history_retention_minutes: int = Field(
        default=60,
        gt=0,
        description="How long to retain resource history",
    )

    cpu_thresholds: ModelResourceThresholds = Field(
        default_factory=ModelResourceThresholds,
        description="CPU-specific thresholds",
    )

    memory_thresholds: ModelResourceThresholds = Field(
        default_factory=ModelResourceThresholds,
        description="Memory-specific thresholds",
    )

    disk_io_thresholds: ModelResourceThresholds = Field(
        default_factory=ModelResourceThresholds,
        description="Disk I/O-specific thresholds",
    )

    composite_weights: dict[str, float] = Field(
        default={"cpu": 0.4, "memory": 0.3, "disk_io": 0.2, "network_io": 0.1},
        description="Weights for computing composite resource score",
    )

    enable_gpu_monitoring: bool = Field(
        default=False,
        description="Whether to monitor GPU resources",
    )

    enable_network_monitoring: bool = Field(
        default=True,
        description="Whether to monitor network I/O",
    )


class ModelResourceMonitorInputState(OnexInputState):
    """Input state for resource monitoring operations."""

    config: ModelResourceMonitorConfig = Field(
        default_factory=ModelResourceMonitorConfig,
        description="Resource monitoring configuration",
    )

    requested_metrics: list[EnumResourceType] = Field(
        default=[
            EnumResourceType.CPU,
            EnumResourceType.MEMORY,
            EnumResourceType.DISK_IO,
        ],
        description="Which resource types to monitor",
    )

    enable_continuous_monitoring: bool = Field(
        default=True,
        description="Whether to start continuous monitoring",
    )


class ModelResourceMonitorOutputState(OnexOutputState):
    """Output state for resource monitoring operations."""

    current_metrics: ModelSystemResourceMetrics = Field(
        description="Current system resource metrics",
    )

    monitoring_active: bool = Field(
        description="Whether continuous monitoring is active",
    )

    next_collection_time: datetime | None = Field(
        default=None,
        description="When next metrics collection is scheduled",
    )

    performance_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Performance summary and recommendations",
    )
