"""
Aggregation configuration model for nodes.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelAggregationConfig(BaseModel):
    """Aggregation configuration for nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = Field(
        ...,
        description="Aggregation strategy (sum, average, max, min, etc.)",
    )
    window_size: int | None = Field(
        None,
        description="Aggregation window size",
        ge=1,
    )
    batch_size: int | None = Field(
        None,
        description="Batch size for aggregation",
        ge=1,
    )
    timeout_ms: int | None = Field(
        None,
        description="Aggregation timeout in milliseconds",
        ge=0,
    )