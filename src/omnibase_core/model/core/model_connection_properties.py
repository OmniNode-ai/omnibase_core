"""
from core.model_masked_connection_properties import ModelMaskedConnectionProperties
from core.model_performance_summary import ModelPerformanceSummary

Connection properties model to replace Dict[str, Any] usage in connection property returns.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer


class ModelConnectionProperties(BaseModel):
    """
    Connection properties with typed fields.
    Replaces Dict[str, Any] for get_connection_properties() returns.
    """

    # Connection identification
    connection_string: Optional[str] = Field(None, description="Full connection string")
    driver: Optional[str] = Field(None, description="Driver name")
    protocol: Optional[str] = Field(None, description="Connection protocol")

    # Server settings
    host: Optional[str] = Field(None, description="Server host")
    port: Optional[int] = Field(None, description="Server port")
    database: Optional[str] = Field(None, description="Database name")
    db_schema: Optional[str] = Field(None, description="Default schema")

    # Authentication
    username: Optional[str] = Field(None, description="Username")
    password: Optional[SecretStr] = Field(None, description="Password")
    auth_mechanism: Optional[str] = Field(None, description="Authentication mechanism")

    # Pool settings
    pool_size: Optional[int] = Field(None, description="Connection pool size")
    max_overflow: Optional[int] = Field(
        None, description="Maximum overflow connections"
    )
    pool_timeout: Optional[int] = Field(None, description="Pool timeout in seconds")
    pool_recycle: Optional[int] = Field(None, description="Connection recycle time")

    # Timeout settings
    connect_timeout: Optional[int] = Field(None, description="Connection timeout")
    socket_timeout: Optional[int] = Field(None, description="Socket timeout")
    command_timeout: Optional[int] = Field(None, description="Command timeout")

    # SSL/TLS settings
    use_ssl: Optional[bool] = Field(None, description="Use SSL/TLS")
    ssl_mode: Optional[str] = Field(None, description="SSL mode")
    ssl_cert: Optional[str] = Field(None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(None, description="SSL key path")
    ssl_ca: Optional[str] = Field(None, description="SSL CA path")

    # Advanced settings
    application_name: Optional[str] = Field(None, description="Application name")
    options: Dict[str, str] = Field(
        default_factory=dict, description="Additional options"
    )

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConnectionProperties":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer("password")
    def serialize_secret(self, value):
        if value and hasattr(value, "get_secret_value"):
            return "***MASKED***"
        return value

    """
    Masked connection properties with typed fields.
    Replaces Dict[str, Any] for get_masked_connection_properties() returns.
    """

    # Same fields as connection properties but with masked sensitive data
    connection_string: Optional[str] = Field(
        None, description="Masked connection string"
    )
    driver: Optional[str] = Field(None, description="Driver name")
    protocol: Optional[str] = Field(None, description="Connection protocol")

    # Server settings (not masked)
    host: Optional[str] = Field(None, description="Server host")
    port: Optional[int] = Field(None, description="Server port")
    database: Optional[str] = Field(None, description="Database name")

    # Authentication (masked)
    username: Optional[str] = Field(None, description="Username (may be masked)")
    password: str = Field("***MASKED***", description="Always masked")
    auth_mechanism: Optional[str] = Field(None, description="Authentication mechanism")

    # Non-sensitive settings
    pool_size: Optional[int] = Field(None, description="Connection pool size")
    use_ssl: Optional[bool] = Field(None, description="Use SSL/TLS")

    # Masking metadata
    masked_fields: List[str] = Field(
        default_factory=list, description="List of masked field names"
    )
    masking_algorithm: str = Field("sha256", description="Masking algorithm used")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    """
    Performance summary with typed fields.
    Replaces Dict[str, Any] for get_performance_summary() returns.
    """

    # Timing metrics
    total_execution_time_ms: float = Field(..., description="Total execution time")
    average_response_time_ms: Optional[float] = Field(
        None, description="Average response time"
    )
    min_response_time_ms: Optional[float] = Field(
        None, description="Minimum response time"
    )
    max_response_time_ms: Optional[float] = Field(
        None, description="Maximum response time"
    )
    p50_response_time_ms: Optional[float] = Field(
        None, description="50th percentile response time"
    )
    p95_response_time_ms: Optional[float] = Field(
        None, description="95th percentile response time"
    )
    p99_response_time_ms: Optional[float] = Field(
        None, description="99th percentile response time"
    )

    # Throughput metrics
    requests_per_second: Optional[float] = Field(
        None, description="Requests per second"
    )
    bytes_per_second: Optional[float] = Field(None, description="Bytes per second")

    # Count metrics
    total_requests: int = Field(0, description="Total number of requests")
    successful_requests: int = Field(0, description="Number of successful requests")
    failed_requests: int = Field(0, description="Number of failed requests")

    # Resource usage
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")

    # Cache metrics
    cache_hits: Optional[int] = Field(None, description="Number of cache hits")
    cache_misses: Optional[int] = Field(None, description="Number of cache misses")
    cache_hit_rate: Optional[float] = Field(
        None, description="Cache hit rate percentage"
    )

    # Error metrics
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    timeout_count: Optional[int] = Field(None, description="Number of timeouts")

    # Time window
    measurement_start: datetime = Field(..., description="Measurement start time")
    measurement_end: datetime = Field(..., description="Measurement end time")
    measurement_duration_seconds: float = Field(..., description="Measurement duration")

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def calculate_average_response_time(self) -> Optional[float]:
        """Calculate average response time if not already set."""
        if self.average_response_time_ms is not None:
            return self.average_response_time_ms

        if self.total_requests > 0 and self.total_execution_time_ms > 0:
            return self.total_execution_time_ms / self.total_requests

        return None

    @field_serializer("measurement_start", "measurement_end")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
