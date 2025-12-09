"""
Logging Subcontract Model.



Dedicated subcontract model for logging functionality providing:
- Log level and format configuration
- Context and correlation tracking
- Performance logging and monitoring
- Sensitive data redaction
- Structured logging and audit trails
- Output destination management

This model is composed into node contracts that require logging functionality,
providing clean separation between node logic and logging behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_log_level_override import ModelLogLevelOverride


class ModelLoggingSubcontract(BaseModel):
    """
    Logging subcontract model for comprehensive logging configuration.

    Provides structured logging, correlation tracking, performance monitoring,
    and security features. Designed for composition into node contracts
    requiring logging functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    log_format: str = Field(
        default="json",
        description="Log format: json, text, key-value",
    )

    # Context and correlation
    enable_context_logging: bool = Field(
        default=True,
        description="Include execution context in log entries",
    )

    enable_correlation_tracking: bool = Field(
        default=True,
        description="Track and propagate correlation IDs",
    )

    correlation_id_field: str = Field(
        default="correlation_id",
        description="Field name for correlation ID in logs",
    )

    # Performance logging
    enable_performance_logging: bool = Field(
        default=True,
        description="Log performance metrics and timing information",
    )

    performance_threshold_ms: int = Field(
        default=1000,
        description="Log warning if operation exceeds threshold (milliseconds)",
        ge=1,
        le=60000,
    )

    track_function_entry_exit: bool = Field(
        default=False,
        description="Log function entry and exit (verbose)",
    )

    # Security and privacy
    enable_sensitive_data_redaction: bool = Field(
        default=True,
        description="Automatically redact sensitive data in logs",
    )

    sensitive_field_patterns: list[str] = Field(
        default_factory=lambda: [
            "password",
            "token",
            "secret",
            "api_key",
            "private_key",
            "ssn",
            "credit_card",
        ],
        description="Patterns to identify sensitive fields for redaction",
    )

    enable_pii_detection: bool = Field(
        default=True,
        description="Enable PII detection and redaction",
    )

    # Structured logging
    structured_logging: bool = Field(
        default=True,
        description="Use structured logging with consistent fields",
    )

    required_log_fields: list[str] = Field(
        default_factory=lambda: [
            "timestamp",
            "level",
            "message",
            "node_name",
        ],
        description="Required fields in every log entry",
    )

    include_stack_trace: bool = Field(
        default=True,
        description="Include stack traces for errors",
    )

    # Audit logging
    enable_audit_logging: bool = Field(
        default=False,
        description="Enable audit trail logging",
    )

    audit_event_types: list[str] = Field(
        default_factory=list,
        description="Event types to include in audit logs",
    )

    # Output configuration
    log_to_console: bool = Field(
        default=True,
        description="Write logs to console/stdout",
    )

    log_to_file: bool = Field(
        default=False,
        description="Write logs to file system",
    )

    log_file_path: str | None = Field(
        default=None,
        description="Path to log file if log_to_file is enabled",
    )

    # Async and performance
    async_logging: bool = Field(
        default=False,
        description="Use asynchronous logging for performance",
    )

    log_buffer_size: int = Field(
        default=1000,
        description="Buffer size for async logging",
        ge=100,
        le=10000,
    )

    flush_interval_ms: int = Field(
        default=5000,
        description="Flush interval for async logging (milliseconds)",
        ge=100,
        le=60000,
    )

    # Size and rotation limits
    max_log_entry_size_kb: int = Field(
        default=64,
        description="Maximum size per log entry in KB",
        ge=1,
        le=1024,
    )

    max_daily_log_size_mb: int = Field(
        default=1024,
        description="Maximum daily log size in MB",
        ge=10,
        le=10240,
    )

    enable_log_rotation: bool = Field(
        default=True,
        description="Enable log rotation",
    )

    rotation_size_mb: int = Field(
        default=100,
        description="Rotate logs when file exceeds size in MB",
        ge=1,
        le=1024,
    )

    # Filtering and sampling
    enable_log_sampling: bool = Field(
        default=False,
        description="Enable log sampling for high-volume scenarios",
    )

    sampling_rate: float = Field(
        default=1.0,
        description="Log sampling rate (0.0 to 1.0, 1.0 = no sampling)",
        ge=0.0,
        le=1.0,
    )

    log_level_overrides: list[ModelLogLevelOverride] = Field(
        default_factory=list,
        description="Strongly-typed per-module or per-logger log level overrides",
    )

    # Integration and enrichment
    include_environment_info: bool = Field(
        default=True,
        description="Include environment information in logs",
    )

    include_node_metadata: bool = Field(
        default=True,
        description="Include node metadata (name, version, type)",
    )

    include_request_context: bool = Field(
        default=True,
        description="Include request context if available",
    )

    @model_validator(mode="after")
    def validate_log_level(self) -> Self:
        """Validate log level is one of allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = self.log_level.upper()
        if v_upper not in allowed:
            msg = f"log_level must be one of {allowed}, got '{self.log_level}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_values": ModelSchemaValue.from_value(allowed),
                        "provided_value": ModelSchemaValue.from_value(self.log_level),
                    },
                ),
            )
        # Use object.__setattr__ to avoid triggering validate_assignment recursion
        object.__setattr__(self, "log_level", v_upper)
        return self

    @model_validator(mode="after")
    def validate_log_format(self) -> Self:
        """Validate log format is one of allowed values."""
        allowed = ["json", "text", "key-value"]
        if self.log_format not in allowed:
            msg = f"log_format must be one of {allowed}, got '{self.log_format}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_values": ModelSchemaValue.from_value(allowed),
                        "provided_value": ModelSchemaValue.from_value(self.log_format),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_performance_threshold(self) -> Self:
        """Validate performance threshold is reasonable."""
        if self.performance_threshold_ms > 30000:
            msg = (
                "performance_threshold_ms exceeding 30 seconds may miss performance issues; "
                "consider using a lower threshold for better monitoring"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "recommended_max_value": ModelSchemaValue.from_value(30000),
                        "provided_value": ModelSchemaValue.from_value(
                            self.performance_threshold_ms
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_sampling_rate(self) -> Self:
        """Validate sampling rate is within valid range."""
        if self.sampling_rate < 0.01:
            msg = (
                "sampling_rate below 0.01 (1%) may lose important log data; "
                "consider using a higher sampling rate"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "minimum_recommended_value": ModelSchemaValue.from_value(0.01),
                        "provided_value": ModelSchemaValue.from_value(
                            self.sampling_rate
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_max_log_entry_size(self) -> Self:
        """Validate max log entry size is reasonable."""
        if self.max_log_entry_size_kb > 512:
            msg = (
                "max_log_entry_size_kb exceeding 512 KB may cause performance issues; "
                "consider splitting large log entries or using external storage"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "recommended_max_value": ModelSchemaValue.from_value(512),
                        "provided_value": ModelSchemaValue.from_value(
                            self.max_log_entry_size_kb
                        ),
                    },
                ),
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
