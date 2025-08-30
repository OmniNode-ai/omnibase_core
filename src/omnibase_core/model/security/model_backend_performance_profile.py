"""
ModelBackendPerformanceProfile: Performance characteristics of secret backends.

This model represents the performance profile of different secret backends.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_latency_level import EnumLatencyLevel
from omnibase_core.enums.enum_overhead_type import EnumOverheadType
from omnibase_core.enums.enum_scalability_level import EnumScalabilityLevel
from omnibase_core.enums.enum_throughput_level import EnumThroughputLevel


class ModelBackendPerformanceProfile(BaseModel):
    """Performance characteristics of a secret backend."""

    latency: EnumLatencyLevel = Field(
        EnumLatencyLevel.MINIMAL, description="Latency level"
    )

    throughput: EnumThroughputLevel = Field(
        EnumThroughputLevel.HIGH, description="Throughput level"
    )

    scalability: EnumScalabilityLevel = Field(
        EnumScalabilityLevel.GOOD, description="Scalability level"
    )

    overhead: EnumOverheadType = Field(
        EnumOverheadType.NONE, description="Overhead type"
    )
