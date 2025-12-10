"""
Metrics Subcontract Model.



Dedicated subcontract model for metrics collection functionality providing:
- Metrics backend configuration (prometheus, statsd, etc.)
- Metric type enablement (histograms, counters, gauges, summaries)
- Collection and export interval management
- Performance monitoring configuration
- Metrics validation and thresholds

This model is composed into node contracts that require metrics functionality,
providing clean separation between node logic and metrics collection behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelMetricsSubcontract(BaseModel):
    """
    Metrics subcontract model for metrics collection functionality.

    Comprehensive metrics subcontract providing backend configuration,
    metric type enablement, collection intervals, and performance monitoring.
    Designed for composition into node contracts requiring metrics functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core metrics configuration
    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection globally",
    )

    metrics_backend: str = Field(
        default="prometheus",
        description="Metrics backend implementation (prometheus, statsd, none)",
    )

    # Metric type enablement
    enable_histograms: bool = Field(
        default=True,
        description="Enable histogram metrics for latency tracking",
    )

    enable_counters: bool = Field(
        default=True,
        description="Enable counter metrics for event counting",
    )

    enable_gauges: bool = Field(
        default=True,
        description="Enable gauge metrics for current values",
    )

    enable_summaries: bool = Field(
        default=False,
        description="Enable summary metrics for statistical distribution",
    )

    # Collection and export intervals
    collection_interval_seconds: int = Field(
        default=60,
        description="Metrics collection interval in seconds",
        ge=1,
        le=3600,
    )

    export_interval_seconds: int = Field(
        default=10,
        description="Metrics export interval in seconds",
        ge=1,
        le=300,
    )

    # Performance monitoring
    enable_performance_metrics: bool = Field(
        default=True,
        description="Enable performance-specific metrics",
    )

    track_response_times: bool = Field(
        default=True,
        description="Track response time metrics",
    )

    track_throughput: bool = Field(
        default=True,
        description="Track throughput metrics",
    )

    track_error_rates: bool = Field(
        default=True,
        description="Track error rate metrics",
    )

    # Metric labels and cardinality
    max_label_cardinality: int = Field(
        default=1000,
        description="Maximum cardinality for metric labels",
        ge=1,
        le=100000,
    )

    enable_custom_labels: bool = Field(
        default=True,
        description="Enable custom metric labels",
    )

    # Aggregation and retention
    aggregation_window_seconds: int = Field(
        default=300,
        description="Aggregation window for metrics in seconds",
        ge=1,
        le=86400,
    )

    retention_period_hours: int = Field(
        default=168,
        description="Metrics retention period in hours (default: 7 days)",
        ge=1,
        le=8760,
    )

    @field_validator("metrics_backend")
    @classmethod
    def validate_metrics_backend(cls, v: str) -> str:
        """Validate metrics backend is one of the supported types."""
        allowed_backends = ["prometheus", "statsd", "none"]
        if v not in allowed_backends:
            msg = f"metrics_backend must be one of {allowed_backends}, got '{v}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_backends": ModelSchemaValue.from_value(
                            str(allowed_backends),
                        ),
                        "received_backend": ModelSchemaValue.from_value(v),
                    },
                ),
            )
        return v

    @model_validator(mode="after")
    def validate_export_interval(self) -> "ModelMetricsSubcontract":
        """Validate export interval is not greater than collection interval."""
        if self.export_interval_seconds > self.collection_interval_seconds:
            msg = f"export_interval_seconds ({self.export_interval_seconds}s) cannot exceed collection_interval_seconds ({self.collection_interval_seconds}s)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "export_interval": ModelSchemaValue.from_value(
                            str(self.export_interval_seconds),
                        ),
                        "collection_interval": ModelSchemaValue.from_value(
                            str(self.collection_interval_seconds),
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
