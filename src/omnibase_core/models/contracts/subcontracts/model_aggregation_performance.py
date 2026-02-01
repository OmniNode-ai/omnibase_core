"""
Aggregation Performance Model.

Individual model for aggregation performance configuration.
Part of the Aggregation Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelAggregationPerformance(BaseModel):
    """
    Aggregation performance configuration.

    Defines performance tuning, optimization,
    and resource management for aggregation operations.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
