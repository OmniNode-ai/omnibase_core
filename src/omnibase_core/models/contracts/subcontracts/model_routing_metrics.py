from pydantic import Field

"""
Routing Metrics Model - ONEX Standards Compliant.

Individual model for routing metrics configuration.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelRoutingMetrics(BaseModel):
    """
    Routing metrics configuration.

    Defines metrics collection, monitoring,
    and alerting for routing operations.
    """

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
