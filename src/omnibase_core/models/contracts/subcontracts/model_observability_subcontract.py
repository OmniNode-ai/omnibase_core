"""
Observability Subcontract Model.



Dedicated subcontract model for observability functionality providing:
- Unified observability configuration (logging, metrics, tracing)
- Distributed tracing with OpenTelemetry support
- Performance profiling and monitoring
- Export format configuration (JSON, OpenTelemetry, etc.)
- Trace sampling and profiling control

This model is composed into node contracts that require comprehensive observability
functionality, integrating logging, metrics, and distributed tracing capabilities.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.observability.model_metrics_policy import ModelMetricsPolicy
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelObservabilitySubcontract(BaseModel):
    """
    Observability subcontract model for comprehensive observability configuration.

    Provides unified configuration for logging, metrics, distributed tracing,
    and performance profiling. Designed for composition into node contracts
    requiring comprehensive observability functionality across all ONEX node types.

    This subcontract enables nodes to:
    - Configure unified observability across all three pillars (logs, metrics, traces)
    - Enable distributed tracing with configurable sampling
    - Profile performance with detailed instrumentation
    - Export telemetry data in multiple formats
    - Control observability overhead through sampling and enablement flags

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Global observability control
    enabled: bool = Field(
        default=True,
        description="Master switch for all observability features",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    enable_structured_logging: bool = Field(
        default=True,
        description="Enable structured logging with consistent fields",
    )

    enable_correlation_tracking: bool = Field(
        default=True,
        description="Track and propagate correlation IDs across operations",
    )

    # Metrics cardinality policy (OMN-1367)
    metrics_policy: ModelMetricsPolicy | None = Field(
        default=None,
        description="Cardinality policy for metrics labels (None disables enforcement)",
    )

    # Distributed tracing configuration
    enable_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing with OpenTelemetry",
    )

    trace_sampling_rate: float = Field(
        default=0.1,
        description="Trace sampling rate (0.0 to 1.0, where 1.0 = trace all requests)",
        ge=0.0,
        le=1.0,
    )

    trace_propagation_format: str = Field(
        default="w3c",
        description="Trace context propagation format: w3c, b3, jaeger",
    )

    trace_exporter_endpoint: str | None = Field(
        default=None,
        description="Endpoint for trace exporter (e.g., OTLP collector endpoint)",
    )

    trace_service_name: str | None = Field(
        default=None,
        description="Service name for distributed tracing (defaults to node name)",
    )

    # Performance profiling
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling and instrumentation",
    )

    profiling_sampling_rate: float = Field(
        default=0.01,
        description="Profiling sampling rate (0.0 to 1.0, where 1.0 = profile all operations)",
        ge=0.0,
        le=1.0,
    )

    profile_cpu: bool = Field(
        default=True,
        description="Enable CPU profiling when profiling is enabled",
    )

    profile_memory: bool = Field(
        default=True,
        description="Enable memory profiling when profiling is enabled",
    )

    profile_io: bool = Field(
        default=False,
        description="Enable I/O profiling when profiling is enabled (higher overhead)",
    )

    profiling_output_path: str | None = Field(
        default=None,
        description="Path for profiling output files (defaults to system temp)",
    )

    # Export configuration
    export_format: str = Field(
        default="json",
        description="Export format for telemetry data: json, opentelemetry, prometheus",
    )

    export_interval_seconds: int = Field(
        default=60,
        description="Interval for exporting telemetry data in seconds",
        ge=1,
        le=3600,
    )

    export_batch_size: int = Field(
        default=100,
        description="Batch size for telemetry export",
        ge=1,
        le=10000,
    )

    export_timeout_seconds: int = Field(
        default=30,
        description="Timeout for export operations in seconds",
        ge=1,
        le=300,
    )

    # Resource attributes
    include_resource_attributes: bool = Field(
        default=True,
        description="Include resource attributes (node name, version, environment) in telemetry",
    )

    include_process_attributes: bool = Field(
        default=True,
        description="Include process attributes (PID, runtime, host) in telemetry",
    )

    custom_resource_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Custom resource attributes to include in all telemetry",
    )

    # Performance and overhead control
    async_export: bool = Field(
        default=True,
        description="Use asynchronous export to reduce performance impact",
    )

    max_queue_size: int = Field(
        default=2048,
        description="Maximum queue size for async telemetry export",
        ge=100,
        le=100000,
    )

    drop_on_queue_full: bool = Field(
        default=True,
        description="Drop telemetry data when queue is full (vs blocking)",
    )

    # Security and privacy
    enable_sensitive_data_redaction: bool = Field(
        default=True,
        description="Automatically redact sensitive data in all telemetry",
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

    # Health and diagnostics
    enable_self_diagnostics: bool = Field(
        default=True,
        description="Enable self-diagnostics for observability system health",
    )

    diagnostics_log_level: str = Field(
        default="WARNING",
        description="Log level for observability system diagnostics",
    )

    @field_validator("log_level", "diagnostics_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            msg = f"log_level must be one of {allowed}, got '{v}'"
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
                        "provided_value": ModelSchemaValue.from_value(v),
                    },
                ),
            )
        return v_upper

    @field_validator("trace_propagation_format")
    @classmethod
    def validate_trace_propagation_format(cls, v: str) -> str:
        """Validate trace propagation format is supported."""
        allowed = ["w3c", "b3", "jaeger"]
        if v not in allowed:
            msg = f"trace_propagation_format must be one of {allowed}, got '{v}'"
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
                        "provided_value": ModelSchemaValue.from_value(v),
                    },
                ),
            )
        return v

    @field_validator("export_format")
    @classmethod
    def validate_export_format(cls, v: str) -> str:
        """Validate export format is supported."""
        allowed = ["json", "opentelemetry", "prometheus"]
        if v not in allowed:
            msg = f"export_format must be one of {allowed}, got '{v}'"
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
                        "provided_value": ModelSchemaValue.from_value(v),
                    },
                ),
            )
        return v

    @model_validator(mode="after")
    def validate_trace_sampling_rate(self) -> Self:
        """Validate trace sampling rate is reasonable for production use."""
        if self.enable_tracing and self.trace_sampling_rate > 0.5:
            msg = (
                "trace_sampling_rate above 0.5 (50%) may cause significant performance overhead; "
                "consider using a lower sampling rate for production workloads"
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
                        "recommended_max_value": ModelSchemaValue.from_value(0.5),
                        "provided_value": ModelSchemaValue.from_value(
                            self.trace_sampling_rate
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_profiling_sampling_rate(self) -> Self:
        """Validate profiling sampling rate is reasonable for production use."""
        if self.enable_profiling and self.profiling_sampling_rate > 0.1:
            msg = (
                "profiling_sampling_rate above 0.1 (10%) may cause significant performance overhead; "
                "consider using a lower sampling rate for production workloads"
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
                        "recommended_max_value": ModelSchemaValue.from_value(0.1),
                        "provided_value": ModelSchemaValue.from_value(
                            self.profiling_sampling_rate
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_tracing_configuration(self) -> Self:
        """Validate tracing is properly configured when enabled."""
        if self.enable_tracing and not self.trace_exporter_endpoint:
            msg = (
                "trace_exporter_endpoint must be provided when enable_tracing is True; "
                "please specify an OTLP collector endpoint or disable tracing"
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
                        "enable_tracing": ModelSchemaValue.from_value(
                            self.enable_tracing
                        ),
                        "trace_exporter_endpoint": ModelSchemaValue.from_value(
                            str(self.trace_exporter_endpoint)
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_profiling_configuration(self) -> Self:
        """Validate profiling has at least one profiler enabled."""
        if self.enable_profiling and not any(
            [self.profile_cpu, self.profile_memory, self.profile_io]
        ):
            msg = (
                "At least one profiler (profile_cpu, profile_memory, profile_io) must be enabled "
                "when enable_profiling is True"
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
                        "enable_profiling": ModelSchemaValue.from_value(
                            self.enable_profiling
                        ),
                        "profile_cpu": ModelSchemaValue.from_value(self.profile_cpu),
                        "profile_memory": ModelSchemaValue.from_value(
                            self.profile_memory
                        ),
                        "profile_io": ModelSchemaValue.from_value(self.profile_io),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_export_interval(self) -> Self:
        """Validate export interval is reasonable."""
        if self.export_interval_seconds < 5:
            msg = (
                "export_interval_seconds below 5 seconds may cause excessive overhead; "
                "consider using a longer interval for better performance"
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
                        "minimum_recommended_value": ModelSchemaValue.from_value(5),
                        "provided_value": ModelSchemaValue.from_value(
                            self.export_interval_seconds
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
