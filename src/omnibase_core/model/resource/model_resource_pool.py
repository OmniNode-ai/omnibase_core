"""
ONEX-compliant model for resource pool management.

Defines resource pools, metrics, and management configurations
for distributed system resource allocation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EnumResourceType(str, Enum):
    """Resource type enumeration."""

    HTTP_CONNECTION = "http_connection"
    DATABASE_CONNECTION = "database_connection"
    MEMORY_BUFFER = "memory_buffer"
    FILE_HANDLE = "file_handle"
    WEBSOCKET_CONNECTION = "websocket_connection"
    THREAD_POOL = "thread_pool"
    PROCESS_POOL = "process_pool"
    CACHE_ENTRY = "cache_entry"


class EnumResourceStatus(str, Enum):
    """Resource status enumeration."""

    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    EXPIRED = "expired"
    ERROR = "error"


class EnumPoolStatus(str, Enum):
    """Resource pool status enumeration."""

    ACTIVE = "active"
    DRAINING = "draining"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"


class ModelResourcePool(BaseModel):
    """
    Resource pool configuration model.

    Manages a pool of resources with allocation, deallocation,
    and lifecycle management following ONEX standards.
    """

    pool_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique pool identifier"
    )
    resource_type: EnumResourceType = Field(
        ..., description="Type of resources in this pool"
    )
    status: EnumPoolStatus = Field(
        EnumPoolStatus.ACTIVE, description="Current pool status"
    )

    # Pool sizing
    min_size: int = Field(1, description="Minimum number of resources to maintain")
    max_size: int = Field(10, description="Maximum number of resources allowed")
    current_size: int = Field(0, description="Current number of resources in pool")
    available_count: int = Field(0, description="Number of available resources")

    # Factory configuration
    factory_function: Optional[str] = Field(
        None, description="Function to create new resources"
    )
    factory_params: dict = Field(
        default_factory=dict, description="Parameters for resource factory"
    )

    # Lifecycle management
    max_idle_time: int = Field(
        1800, description="Max idle time before cleanup (seconds)"
    )
    max_lifetime: int = Field(7200, description="Max resource lifetime (seconds)")
    health_check_interval: int = Field(
        300, description="Health check interval (seconds)"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now, description="Pool creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )
    last_health_check: Optional[datetime] = Field(
        None, description="Last health check time"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "pool_id": "550e8400-e29b-41d4-a716-446655440000",
                "resource_type": "http_connection",
                "status": "active",
                "min_size": 2,
                "max_size": 20,
                "current_size": 5,
                "available_count": 3,
                "factory_function": "create_http_client",
                "factory_params": {"timeout": 30, "max_connections": 100},
                "max_idle_time": 1800,
                "max_lifetime": 7200,
                "health_check_interval": 300,
                "created_at": "2025-07-30T12:00:00Z",
                "updated_at": "2025-07-30T12:30:00Z",
            }
        }


class ModelResourceMetrics(BaseModel):
    """
    Resource usage metrics model.

    Tracks resource allocation, usage patterns, and performance
    metrics for monitoring and optimization.
    """

    # Resource counts
    active_count: int = Field(0, description="Number of active resources")
    pool_count: int = Field(0, description="Number of resource pools")
    total_acquired: int = Field(0, description="Total resources acquired")
    total_released: int = Field(0, description="Total resources released")

    # System metrics
    memory_usage_mb: float = Field(0.0, description="Current memory usage in MB")
    cpu_usage_percent: float = Field(0.0, description="Current CPU usage percentage")

    # Performance metrics
    average_acquisition_time: float = Field(
        0.0, description="Average resource acquisition time (ms)"
    )
    average_release_time: float = Field(
        0.0, description="Average resource release time (ms)"
    )

    # Health indicators
    allocation_failures: int = Field(0, description="Number of allocation failures")
    resource_leaks: int = Field(0, description="Number of detected resource leaks")
    cleanup_operations: int = Field(
        0, description="Number of cleanup operations performed"
    )

    # Timestamps
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last metrics update"
    )
    monitoring_started: datetime = Field(
        default_factory=datetime.now, description="Monitoring start time"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "active_count": 15,
                "pool_count": 3,
                "total_acquired": 1250,
                "total_released": 1235,
                "memory_usage_mb": 456.7,
                "cpu_usage_percent": 23.4,
                "average_acquisition_time": 12.5,
                "average_release_time": 3.2,
                "allocation_failures": 2,
                "resource_leaks": 0,
                "cleanup_operations": 45,
                "last_updated": "2025-07-30T12:35:00Z",
                "monitoring_started": "2025-07-30T10:00:00Z",
            }
        }


class ModelResourceAllocation(BaseModel):
    """
    Resource allocation request model.

    Represents a request for resource allocation with
    requirements and constraints.
    """

    allocation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique allocation identifier"
    )
    resource_type: EnumResourceType = Field(
        ..., description="Type of resource requested"
    )
    requested_at: datetime = Field(
        default_factory=datetime.now, description="Request timestamp"
    )

    # Requirements
    min_count: int = Field(1, description="Minimum number of resources required")
    max_count: int = Field(1, description="Maximum number of resources allowed")
    timeout_seconds: float = Field(30.0, description="Allocation timeout in seconds")

    # Constraints
    tags: dict = Field(
        default_factory=dict, description="Resource tags and constraints"
    )
    priority: int = Field(5, description="Allocation priority (1-10, 1=highest)")

    # Allocation result
    allocated_resource_ids: list = Field(
        default_factory=list, description="IDs of allocated resources"
    )
    status: str = Field("pending", description="Allocation status")
    error_message: Optional[str] = Field(
        None, description="Error message if allocation failed"
    )

    # Lifecycle
    expires_at: Optional[datetime] = Field(None, description="When allocation expires")
    completed_at: Optional[datetime] = Field(
        None, description="When allocation completed"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "allocation_id": "alloc_123456",
                "resource_type": "http_connection",
                "requested_at": "2025-07-30T12:00:00Z",
                "min_count": 1,
                "max_count": 3,
                "timeout_seconds": 30.0,
                "tags": {"environment": "production", "service": "api_client"},
                "priority": 3,
                "allocated_resource_ids": ["res_001", "res_002"],
                "status": "completed",
                "expires_at": "2025-07-30T14:00:00Z",
                "completed_at": "2025-07-30T12:00:15Z",
            }
        }
