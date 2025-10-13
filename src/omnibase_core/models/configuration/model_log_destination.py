from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_log_destination_config import (
    ModelLogDestinationConfig,
)


class ModelLogDestination(BaseModel):
    """Log output destination configuration."""

    destination_type: str = Field(
        default=...,
        description="Destination type",
        pattern="^(console|file|syslog|network|database|custom)$",
    )
    destination_name: str = Field(
        default=..., description="Unique destination identifier"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this destination is enabled",
    )
    file_path: str | None = Field(
        default=None,
        description="File path for file destinations",
    )
    host: str | None = Field(default=None, description="Host for network destinations")
    port: int | None = Field(
        default=None,
        description="Port for network destinations",
        ge=1,
        le=65535,
    )
    connection_string: str | None = Field(
        default=None,
        description="Connection string for database destinations",
    )
    configuration: ModelLogDestinationConfig = Field(
        default_factory=lambda: ModelLogDestinationConfig(),
        description="Additional destination-specific configuration",
    )
    buffer_size: int = Field(
        default=1000,
        description="Buffer size for batched logging",
        ge=1,
    )
    flush_interval_ms: int = Field(
        default=5000,
        description="Flush interval in milliseconds",
        ge=100,
    )

    def is_network_destination(self) -> bool:
        """Check if this is a network-based destination."""
        return self.destination_type in ("network", "syslog")

    def requires_connection(self) -> bool:
        """Check if this destination requires a connection."""
        return self.destination_type in ("network", "database", "syslog")

    @classmethod
    def create_console(cls, name: str = "console") -> "ModelLogDestination":
        """Factory method for console destination."""
        return cls(destination_type="console", destination_name=name)

    @classmethod
    def create_file(cls, name: str, file_path: str) -> "ModelLogDestination":
        """Factory method for file destination."""
        return cls(destination_type="file", destination_name=name, file_path=file_path)

    @classmethod
    def create_network(cls, name: str, host: str, port: int) -> "ModelLogDestination":
        """Factory method for network destination."""
        return cls(
            destination_type="network",
            destination_name=name,
            host=host,
            port=port,
        )
