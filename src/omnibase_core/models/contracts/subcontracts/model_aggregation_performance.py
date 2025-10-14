from pydantic import Field

"""
Aggregation Performance Model - ONEX Standards Compliant.

Individual model for aggregation performance configuration.
Part of the Aggregation Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelAggregationPerformance(BaseModel):
    """
    Aggregation performance configuration.

    Defines performance tuning, optimization,
    and resource management for aggregation operations.
    """

    parallel_aggregation: bool = Field(
        default=True,
        description="Enable parallel aggregation processing",
    )

    max_parallel_workers: int = Field(
        default=4,
        description="Maximum parallel workers",
        ge=1,
        le=32,
    )

    batch_size: int = Field(
        default=1000,
        description="Batch size for aggregation processing",
        ge=1,
    )

    memory_limit_mb: int = Field(
        default=1024,
        description="Memory limit for aggregation operations",
        ge=64,
    )

    spill_to_disk: bool = Field(
        default=False,
        description="Enable spilling to disk for large aggregations",
    )

    compression_enabled: bool = Field(
        default=False,
        description="Enable compression for aggregation data",
    )

    caching_intermediate_results: bool = Field(
        default=True,
        description="Cache intermediate aggregation results",
    )

    lazy_evaluation: bool = Field(
        default=False,
        description="Enable lazy evaluation of aggregations",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
