"""Graph Health Status Model.

Type-safe model representing the health status of a graph database connection.

Thread Safety:
    ModelGraphHealthStatus instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphHealthStatus(BaseModel):
    """Represents the health status of a graph database connection.

    Contains connection health information including latency,
    database version, and connection pool statistics.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    healthy: bool = Field(
        default=False,
        description="Whether the database connection is healthy",
    )
    latency_ms: float = Field(
        default=0.0,
        description="Connection latency in milliseconds",
        ge=0.0,
    )
    # ONEX_EXCLUDE: string_version - This is a raw version string from external database
    # (e.g., Neo4j "4.4.0", Memgraph "2.5.0") which may not conform to SemVer format.
    # We intentionally use str here to capture the database's native version format.
    database_version: str | None = Field(
        default=None,
        description="Version string of the graph database (e.g., '4.4.0' for Neo4j)",
    )
    connection_count: int = Field(
        default=0,
        description="Number of active connections in the pool",
        ge=0,
    )


__all__ = ["ModelGraphHealthStatus"]
