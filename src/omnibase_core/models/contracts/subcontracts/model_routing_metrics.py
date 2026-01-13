"""
Routing Metrics Model.

Individual model for routing metrics configuration.
Part of the Routing Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelRoutingMetrics(BaseModel):
    """
    Routing metrics configuration.

    Defines metrics collection, monitoring,
    and alerting for routing operations.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    metrics_enabled: bool = Field(
        default=True,
        description="Enable routing metrics collection",
    )

    detailed_metrics: bool = Field(
        default=False,
        description="Enable detailed per-route metrics",
    )

    latency_buckets: list[float] = Field(
        default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        description="Latency histogram buckets",
    )

    error_rate_threshold: float = Field(
        default=0.05,
        description="Error rate alerting threshold",
        ge=0.0,
        le=1.0,
    )

    latency_threshold_ms: int = Field(
        default=5000,
        description="Latency alerting threshold",
        ge=100,
    )

    sampling_rate: float = Field(
        default=1.0,
        description="Metrics sampling rate",
        ge=0.0,
        le=1.0,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
