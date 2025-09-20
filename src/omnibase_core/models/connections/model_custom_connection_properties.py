"""
Custom connection properties model for connection configuration.
"""

from pydantic import BaseModel, Field
from ..core.model_custom_properties import ModelCustomProperties


class ModelCustomConnectionProperties(BaseModel):
    """Custom properties for connection configuration."""

    # Database-specific
    database_name: str | None = Field(default=None, description="Database name")
    schema_name: str | None = Field(default=None, description="Schema name")
    charset: str | None = Field(default=None, description="Character set")
    collation: str | None = Field(default=None, description="Collation")

    # Message queue specific
    queue_name: str | None = Field(default=None, description="Queue/topic name")
    exchange_name: str | None = Field(default=None, description="Exchange name")
    routing_key: str | None = Field(default=None, description="Routing key")
    durable: bool | None = Field(default=None, description="Durable queue/exchange")

    # Cloud/service specific
    region: str | None = Field(default=None, description="Cloud region")
    availability_zone: str | None = Field(default=None, description="Availability zone")
    service_name: str | None = Field(default=None, description="Service name")
    instance_type: str | None = Field(default=None, description="Instance type")

    # Performance tuning
    max_connections: int | None = Field(default=None, description="Maximum connections")
    connection_limit: int | None = Field(default=None, description="Connection limit")
    command_timeout: int | None = Field(default=None, description="Command timeout")

    # Compression and optimization
    enable_compression: bool | None = Field(
        default=None,
        description="Enable compression",
    )
    compression_level: int | None = Field(default=None, description="Compression level")
    enable_caching: bool | None = Field(default=None, description="Enable caching")

    # Generic custom properties
    custom_properties: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Additional custom properties with type safety",
    )
