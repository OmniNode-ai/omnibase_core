from pydantic import BaseModel, Field


class ModelLogDestinationConfig(BaseModel):
    """Configuration for log destinations."""

    # File destination options
    max_file_size_mb: int | None = Field(
        None,
        description="Maximum file size in MB before rotation",
        ge=1,
    )
    max_files: int | None = Field(
        None,
        description="Maximum number of rotated files to keep",
        ge=1,
    )
    file_permissions: str | None = Field(
        None,
        description="File permissions (octal string like '0644')",
    )
    compress_rotated: bool = Field(False, description="Compress rotated log files")

    # Network destination options
    protocol: str | None = Field(
        None,
        description="Network protocol",
        pattern="^(tcp|udp|http|https)$",
    )
    timeout_ms: int | None = Field(
        None,
        description="Connection timeout in milliseconds",
        ge=100,
    )
    retry_attempts: int = Field(3, description="Number of retry attempts", ge=0, le=10)
    use_tls: bool = Field(False, description="Use TLS for network connections")
    verify_certificate: bool = Field(True, description="Verify TLS certificates")

    # Database destination options
    table_name: str | None = Field(None, description="Database table name for logs")
    batch_insert: bool = Field(
        True,
        description="Use batch inserts for better performance",
    )
    create_table_if_missing: bool = Field(
        False,
        description="Create log table if it doesn't exist",
    )

    # Formatting options
    include_timestamp: bool = Field(True, description="Include timestamp in output")
    timestamp_format: str = Field(
        "%Y-%m-%d %H:%M:%S.%f",
        description="Timestamp format string",
    )
    include_hostname: bool = Field(False, description="Include hostname in output")

    # Custom destination options
    custom_handler_class: str | None = Field(
        None,
        description="Fully qualified class name for custom handler",
    )
    custom_handler_config: dict[str, str] | None = Field(
        None,
        description="Configuration for custom handler",
    )


class ModelLogDestination(BaseModel):
    """Log output destination configuration."""

    destination_type: str = Field(
        ...,
        description="Destination type",
        pattern="^(console|file|syslog|network|database|custom)$",
    )
    destination_name: str = Field(..., description="Unique destination identifier")
    enabled: bool = Field(
        default=True,
        description="Whether this destination is enabled",
    )
    file_path: str | None = Field(
        None,
        description="File path for file destinations",
    )
    host: str | None = Field(None, description="Host for network destinations")
    port: int | None = Field(
        None,
        description="Port for network destinations",
        ge=1,
        le=65535,
    )
    connection_string: str | None = Field(
        None,
        description="Connection string for database destinations",
    )
    configuration: ModelLogDestinationConfig = Field(
        default_factory=ModelLogDestinationConfig,
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
