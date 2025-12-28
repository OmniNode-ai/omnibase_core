"""
ModelChainMetrics: Metrics for signature chain operations.

This model tracks performance and operational metrics for signature chains
with structured metric fields.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelChainMetrics(BaseModel):
    """Metrics for signature chain operations.

    Note:
        This model uses frozen=True for immutability and from_attributes=True
        to support pytest-xdist parallel execution where class identity may
        differ between workers.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    total_signatures: int = Field(default=0, description="Total signatures in chain")
    valid_signatures: int = Field(default=0, description="Number of valid signatures")
    verification_time_ms: float = Field(
        default=0.0,
        description="Total verification time",
    )
    chain_build_time_ms: float | None = Field(
        default=None,
        description="Time to build chain",
    )
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate percentage",
    )
