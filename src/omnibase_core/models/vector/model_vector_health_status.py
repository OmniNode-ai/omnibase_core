"""Vector store health status model.

This module provides the ModelVectorHealthStatus class for representing
the health status of a vector store backend.

Thread Safety:
    ModelVectorHealthStatus instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelVectorHealthStatus(BaseModel):
    """Health status of a vector store backend.

    This model represents the health check results for a vector database,
    including connectivity, latency, and index information.

    Attributes:
        healthy: Whether the vector store is healthy and operational.
        latency_ms: Round-trip latency to the vector store in milliseconds.
        details: Additional health check details as key-value pairs.
        indices: List of available index names in the vector store.
        last_error: Last error message if unhealthy, None if healthy.

    Example:
        Healthy status::

            from omnibase_core.models.vector import ModelVectorHealthStatus
            from omnibase_core.models.common import ModelSchemaValue

            status = ModelVectorHealthStatus(
                healthy=True,
                latency_ms=15,
                details={
                    "version": ModelSchemaValue.from_value("1.8.0"),
                    "disk_usage": ModelSchemaValue.from_value("45%"),
                },
                indices=["documents", "images", "products"],
            )

        Unhealthy status::

            status = ModelVectorHealthStatus(
                healthy=False,
                latency_ms=5000,
                details={},
                indices=[],
                last_error="Connection timeout after 5000ms",
            )
    """

    healthy: bool = Field(
        ...,
        description="Whether the vector store is healthy and operational",
    )
    latency_ms: int = Field(
        ...,
        ge=0,
        description="Round-trip latency in milliseconds",
    )
    details: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional health check details",
    )
    indices: list[str] = Field(
        default_factory=list,
        description="List of available index names",
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message if unhealthy",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorHealthStatus"]
