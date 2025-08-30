"""
ModelChainMetrics: Metrics for signature chain operations.

This model tracks performance and operational metrics for signature chains
with structured metric fields.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelChainMetrics(BaseModel):
    """Metrics for signature chain operations."""

    total_signatures: int = Field(default=0, description="Total signatures in chain")
    valid_signatures: int = Field(default=0, description="Number of valid signatures")
    verification_time_ms: float = Field(
        default=0.0, description="Total verification time"
    )
    chain_build_time_ms: Optional[float] = Field(
        None, description="Time to build chain"
    )
    cache_hit_rate: Optional[float] = Field(
        None, description="Cache hit rate percentage"
    )
