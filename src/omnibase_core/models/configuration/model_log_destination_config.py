from pydantic import BaseModel, Field


class ModelLogDestinationConfig(BaseModel):
    """Configuration for log destinations."""

    # File destination options
    max_file_size_mb: int | None = Field(
        default=None,
        description="Maximum file size in MB before rotation",
        ge=1,
    )
    max_files: int | None = Field(
        default=None,
        description="Maximum number of rotated files to keep",
        ge=1,
    )
    file_permissions: str | None = Field(
        default=None,
        description="File permissions (octal string like '0644')",
    )
    compress_rotated: bool = Field(
        default=False, description="Compress rotated log files"
    )

    # Network destination options
    protocol: str | None = Field(
        default=None,
        description="Network protocol",
        pattern="^(tcp|udp|http|https)$",
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Connection timeout in milliseconds",
        ge=100,
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts", ge=0, le=10
    )
    use_tls: bool = Field(default=False, description="Use TLS for network connections")
    verify_certificate: bool = Field(
        default=True, description="Verify TLS certificates"
    )

    # Database destination options
    table_name: str | None = Field(
        default=None, description="Database table name for logs"
    )
    batch_insert: bool = Field(
        default=True,
        description="Use batch inserts for better performance",
    )
    create_table_if_missing: bool = Field(
        default=False,
        description="Create log table if it doesn't exist",
    )

    # Formatting options
    include_timestamp: bool = Field(
        default=True, description="Include timestamp in output"
    )
    timestamp_format: str = Field(
        default="%Y-%m-%d %H:%M:%S.%f",
        description="Timestamp format string",
    )
    include_hostname: bool = Field(
        default=False, description="Include hostname in output"
    )

    # Custom destination options
    custom_handler_class: str | None = Field(
        default=None,
        description="Fully qualified class name for custom handler",
    )
    custom_handler_config: dict[str, str] | None = Field(
        default=None,
        description="Configuration for custom handler",
    )
