"""
from core.model_masked_connection_properties import ModelMaskedConnectionProperties
from core.model_performance_summary import ModelPerformanceSummary

Connection properties model to replace Dict[str, Any] usage in connection property returns.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelConnectionProperties(BaseModel):
    """
    Connection properties with typed fields.
    Replaces Dict[str, Any] for get_connection_properties() returns.
    """

    # Connection identification
    connection_string: str | None = Field(
        default=None, description="Full connection string"
    )
    driver: str | None = Field(default=None, description="Driver name")
    protocol: str | None = Field(default=None, description="Connection protocol")

    # Server settings
    host: str | None = Field(default=None, description="Server host")
    port: int | None = Field(default=None, description="Server port")
    database: str | None = Field(default=None, description="Database name")
    db_schema: str | None = Field(default=None, description="Default schema")

    # Authentication
    username: str | None = Field(default=None, description="Username")
    password: SecretStr | None = Field(default=None, description="Password")
    auth_mechanism: str | None = Field(
        default=None, description="Authentication mechanism"
    )

    # Pool settings
    pool_size: int | None = Field(default=None, description="Connection pool size")
    max_overflow: int | None = Field(
        default=None,
        description="Maximum overflow connections",
    )
    pool_timeout: int | None = Field(
        default=None, description="Pool timeout in seconds"
    )
    pool_recycle: int | None = Field(
        default=None, description="Connection recycle time"
    )

    # Timeout settings
    connect_timeout: int | None = Field(default=None, description="Connection timeout")
    socket_timeout: int | None = Field(default=None, description="Socket timeout")
    command_timeout: int | None = Field(default=None, description="Command timeout")

    # SSL/TLS settings
    use_ssl: bool | None = Field(default=None, description="Use SSL/TLS")
    ssl_mode: str | None = Field(default=None, description="SSL mode")
    ssl_cert: str | None = Field(default=None, description="SSL certificate path")
    ssl_key: str | None = Field(default=None, description="SSL key path")
    ssl_ca: str | None = Field(default=None, description="SSL CA path")

    # Advanced settings
    application_name: str | None = Field(default=None, description="Application name")
    options: dict[str, str] = Field(
        default_factory=dict,
        description="Additional options",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @classmethod
    def from_dict(cls, data: "SerializedDict") -> "ModelConnectionProperties":
        """Create from dictionary for easy migration."""
        return cls.model_validate(data)

    @field_serializer("password")
    def serialize_secret(self, value: SecretStr | str | None) -> str:
        from typing import cast

        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return cast("str", value)

    """
    Masked connection properties with typed fields.
    Replaces Dict[str, Any] for get_masked_connection_properties() returns.
    """

    # Same fields as connection properties but with masked sensitive data

    # Server settings (not masked)

    # Authentication (masked)

    # Non-sensitive settings

    # Masking metadata
    masked_fields: list[str] = Field(
        default_factory=list,
        description="List of masked field names",
    )
    masking_algorithm: str = Field(
        default="sha256", description="Masking algorithm used"
    )
    """
    Performance summary with typed fields.
    Replaces Dict[str, Any] for get_performance_summary() returns.
    """

    # Timing metrics
    total_execution_time_ms: float = Field(
        default=..., description="Total execution time"
    )
    average_response_time_ms: float | None = Field(
        default=None,
        description="Average response time",
    )
    min_response_time_ms: float | None = Field(
        default=None,
        description="Minimum response time",
    )
    max_response_time_ms: float | None = Field(
        default=None,
        description="Maximum response time",
    )
    p50_response_time_ms: float | None = Field(
        default=None,
        description="50th percentile response time",
    )
    p95_response_time_ms: float | None = Field(
        default=None,
        description="95th percentile response time",
    )
    p99_response_time_ms: float | None = Field(
        default=None,
        description="99th percentile response time",
    )

    # Throughput metrics
    requests_per_second: float | None = Field(
        default=None,
        description="Requests per second",
    )
    bytes_per_second: float | None = Field(default=None, description="Bytes per second")

    # Count metrics
    total_requests: int = Field(default=0, description="Total number of requests")
    successful_requests: int = Field(
        default=0, description="Number of successful requests"
    )
    failed_requests: int = Field(default=0, description="Number of failed requests")

    # Resource usage
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )

    # Cache metrics
    cache_hits: int | None = Field(default=None, description="Number of cache hits")
    cache_misses: int | None = Field(default=None, description="Number of cache misses")
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate percentage",
    )

    # Error metrics
    error_rate: float | None = Field(default=None, description="Error rate percentage")
    timeout_count: int | None = Field(default=None, description="Number of timeouts")

    # Time window
    measurement_start: datetime = Field(
        default=..., description="Measurement start time"
    )
    measurement_end: datetime = Field(default=..., description="Measurement end time")
    measurement_duration_seconds: float = Field(
        default=..., description="Measurement duration"
    )

    def get_success_rate(self) -> float:
        """Get success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def get_average_response_time(self) -> float | None:
        """Get average response time if not already set."""
        if self.average_response_time_ms is not None:
            return self.average_response_time_ms

        if self.total_requests > 0 and self.total_execution_time_ms > 0:
            return self.total_execution_time_ms / self.total_requests

        return None

    @field_serializer("measurement_start", "measurement_end")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
