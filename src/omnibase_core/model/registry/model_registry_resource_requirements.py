"""
Registry Resource Requirements Model

Type-safe resource requirements for registry resolution.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelRegistryResourceRequirements(BaseModel):
    """
    Type-safe resource requirements for registry resolution.

    Estimates resource needs for resolution operations.
    """

    cpu_score: int = Field(
        ..., description="CPU requirement score (1-10 scale)", ge=1, le=10
    )

    memory_score: int = Field(
        ..., description="Memory requirement score (1-10 scale)", ge=1, le=10
    )

    network_required: bool = Field(
        False, description="Whether network access is required"
    )

    disk_space_score: int = Field(
        1, description="Disk space requirement score (1-10 scale)", ge=1, le=10
    )

    estimated_duration_seconds: int = Field(
        ..., description="Estimated duration in seconds", ge=1
    )

    # Additional resource details
    min_memory_mb: Optional[int] = Field(
        None, description="Minimum memory in megabytes", ge=1
    )

    recommended_memory_mb: Optional[int] = Field(
        None, description="Recommended memory in megabytes", ge=1
    )

    min_cpu_cores: Optional[float] = Field(None, description="Minimum CPU cores", gt=0)

    recommended_cpu_cores: Optional[float] = Field(
        None, description="Recommended CPU cores", gt=0
    )

    disk_iops_required: Optional[int] = Field(
        None, description="Disk IOPS required", ge=0
    )

    network_bandwidth_mbps: Optional[float] = Field(
        None, description="Network bandwidth required in Mbps", ge=0
    )

    gpu_required: bool = Field(False, description="Whether GPU is required")

    gpu_memory_gb: Optional[float] = Field(
        None, description="GPU memory required in GB", gt=0
    )

    special_requirements: List[str] = Field(
        default_factory=list,
        description="Special resource requirements (e.g., 'high-iops', 'low-latency')",
    )
