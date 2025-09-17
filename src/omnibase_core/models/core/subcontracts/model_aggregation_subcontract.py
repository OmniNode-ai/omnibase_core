#!/usr/bin/env python3
"""
Aggregation Subcontract Model - ONEX Standards Compliant.

Dedicated subcontract model for data aggregation functionality providing:
- Aggregation function definitions and configurations
- Data grouping and windowing strategies
- Statistical computation specifications
- Aggregation performance and optimization
- Real-time and batch aggregation support

This model is composed into node contracts that require aggregation functionality,
providing clean separation between node logic and aggregation behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, field_validator


class ModelAggregationFunction(BaseModel):
    """
    Aggregation function definition.

    Defines aggregation functions, parameters,
    and computational requirements for data processing.
    """

    function_name: str = Field(
        ...,
        description="Name of the aggregation function",
        min_length=1,
    )

    function_type: str = Field(
        ...,
        description="Type of function (statistical, mathematical, custom)",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable function description",
        min_length=1,
    )

    input_fields: list[str] = Field(
        ...,
        description="Required input fields for function",
        min_length=1,
    )

    output_field: str = Field(
        ...,
        description="Output field name for result",
        min_length=1,
    )

    parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Function-specific parameters",
    )

    null_handling: str = Field(
        default="ignore",
        description="Strategy for handling null values",
    )

    precision_digits: int = Field(
        default=6,
        description="Precision for numeric results",
        ge=1,
        le=15,
    )

    requires_sorting: bool = Field(
        default=False,
        description="Whether function requires sorted input",
    )

    is_associative: bool = Field(
        default=False,
        description="Whether function is associative",
    )

    is_commutative: bool = Field(
        default=False,
        description="Whether function is commutative",
    )


class ModelDataGrouping(BaseModel):
    """
    Data grouping configuration.

    Defines grouping strategies, keys, and
    aggregation scope for data processing.
    """

    grouping_enabled: bool = Field(default=True, description="Enable data grouping")

    grouping_fields: list[str] = Field(
        default_factory=list,
        description="Fields to group by for aggregation",
    )

    grouping_strategy: str = Field(
        default="hash_based",
        description="Strategy for data grouping",
    )

    case_sensitive_grouping: bool = Field(
        default=True,
        description="Case sensitivity for grouping keys",
    )

    null_group_handling: str = Field(
        default="separate",
        description="How to handle null grouping values",
    )

    max_groups: int | None = Field(
        default=None,
        description="Maximum number of groups to maintain",
        ge=1,
    )

    group_expiration_ms: int | None = Field(
        default=None,
        description="Expiration time for inactive groups",
        ge=1000,
    )


class ModelWindowingStrategy(BaseModel):
    """
    Windowing strategy for time-based aggregation.

    Defines windowing policies, sizes, and
    time-based aggregation parameters.
    """

    windowing_enabled: bool = Field(
        default=False,
        description="Enable windowing for aggregation",
    )

    window_type: str = Field(
        default="tumbling",
        description="Type of windowing (tumbling, sliding, session)",
    )

    window_size_ms: int = Field(
        default=60000,
        description="Window size in milliseconds",
        ge=1000,
    )

    window_slide_ms: int | None = Field(
        default=None,
        description="Window slide interval for sliding windows",
        ge=1000,
    )

    session_timeout_ms: int | None = Field(
        default=None,
        description="Session timeout for session windows",
        ge=1000,
    )

    window_trigger: str = Field(
        default="time_based",
        description="Trigger for window completion",
    )

    late_arrival_handling: str = Field(
        default="ignore",
        description="Strategy for late-arriving data",
    )

    allowed_lateness_ms: int = Field(
        default=10000,
        description="Allowed lateness for events",
        ge=0,
    )

    watermark_strategy: str = Field(
        default="event_time",
        description="Watermark strategy for event ordering",
    )


class ModelStatisticalComputation(BaseModel):
    """
    Statistical computation configuration.

    Defines statistical functions, approximations,
    and advanced analytical computations.
    """

    statistical_enabled: bool = Field(
        default=False,
        description="Enable statistical computations",
    )

    statistical_functions: list[str] = Field(
        default_factory=list,
        description="Statistical functions to compute",
    )

    percentiles: list[float] = Field(
        default_factory=list,
        description="Percentiles to calculate",
    )

    approximation_enabled: bool = Field(
        default=False,
        description="Enable approximation algorithms",
    )

    approximation_error_tolerance: float = Field(
        default=0.01,
        description="Error tolerance for approximations",
        ge=0.001,
        le=0.1,
    )

    histogram_enabled: bool = Field(
        default=False,
        description="Enable histogram computation",
    )

    histogram_buckets: int = Field(
        default=10,
        description="Number of histogram buckets",
        ge=2,
    )

    outlier_detection: bool = Field(
        default=False,
        description="Enable outlier detection",
    )

    outlier_threshold: float = Field(
        default=2.0,
        description="Threshold for outlier detection",
        ge=0.5,
    )


class ModelAggregationPerformance(BaseModel):
    """
    Aggregation performance configuration.

    Defines performance tuning, optimization,
    and resource management for aggregation operations.
    """

    parallel_aggregation: bool = Field(
        default=True,
        description="Enable parallel aggregation processing",
    )

    max_parallel_workers: int = Field(
        default=4,
        description="Maximum parallel workers",
        ge=1,
        le=32,
    )

    batch_size: int = Field(
        default=1000,
        description="Batch size for aggregation processing",
        ge=1,
    )

    memory_limit_mb: int = Field(
        default=1024,
        description="Memory limit for aggregation operations",
        ge=64,
    )

    spill_to_disk: bool = Field(
        default=False,
        description="Enable spilling to disk for large aggregations",
    )

    compression_enabled: bool = Field(
        default=False,
        description="Enable compression for aggregation data",
    )

    caching_intermediate_results: bool = Field(
        default=True,
        description="Cache intermediate aggregation results",
    )

    lazy_evaluation: bool = Field(
        default=False,
        description="Enable lazy evaluation of aggregations",
    )


class ModelAggregationSubcontract(BaseModel):
    """
    Aggregation subcontract model for data aggregation functionality.

    Comprehensive aggregation subcontract providing aggregation functions,
    grouping strategies, windowing, and statistical computations.
    Designed for composition into node contracts requiring aggregation functionality.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core aggregation configuration
    aggregation_enabled: bool = Field(
        default=True,
        description="Enable aggregation functionality",
    )

    aggregation_mode: str = Field(
        default="batch",
        description="Aggregation mode (batch, streaming, hybrid)",
    )

    # Aggregation functions
    aggregation_functions: list[str] = Field(
        ...,
        description="List of aggregation functions to apply",
        min_length=1,
    )

    function_definitions: list[ModelAggregationFunction] = Field(
        default_factory=list,
        description="Detailed function definitions",
    )

    # Data grouping configuration
    grouping: ModelDataGrouping = Field(
        default_factory=ModelDataGrouping,
        description="Data grouping configuration",
    )

    # Windowing strategy (for time-based aggregations)
    windowing: ModelWindowingStrategy | None = Field(
        default=None,
        description="Windowing strategy configuration",
    )

    # Statistical computations
    statistical: ModelStatisticalComputation | None = Field(
        default=None,
        description="Statistical computation configuration",
    )

    # Performance optimization
    performance: ModelAggregationPerformance = Field(
        default_factory=ModelAggregationPerformance,
        description="Performance optimization configuration",
    )

    # Data handling and quality
    null_handling_strategy: str = Field(
        default="ignore",
        description="Global strategy for handling null values",
    )

    duplicate_handling: str = Field(
        default="include",
        description="Strategy for handling duplicate values",
    )

    data_validation_enabled: bool = Field(
        default=True,
        description="Enable input data validation",
    )

    schema_enforcement: bool = Field(
        default=True,
        description="Enforce schema validation for input data",
    )

    # Output configuration
    output_format: str = Field(
        default="structured",
        description="Format for aggregation output",
    )

    result_caching: bool = Field(
        default=True,
        description="Enable caching of aggregation results",
    )

    result_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cached results",
        ge=1,
    )

    incremental_updates: bool = Field(
        default=False,
        description="Enable incremental result updates",
    )

    # Monitoring and metrics
    metrics_enabled: bool = Field(
        default=True,
        description="Enable aggregation metrics",
    )

    performance_monitoring: bool = Field(
        default=True,
        description="Monitor aggregation performance",
    )

    memory_usage_tracking: bool = Field(
        default=False,
        description="Track memory usage during aggregation",
    )

    # Error handling and recovery
    error_handling_strategy: str = Field(
        default="continue",
        description="Strategy for handling aggregation errors",
    )

    partial_results_on_error: bool = Field(
        default=True,
        description="Return partial results on error",
    )

    retry_failed_aggregations: bool = Field(
        default=False,
        description="Retry failed aggregation operations",
    )

    max_retries: int = Field(default=3, description="Maximum retry attempts", ge=0)

    @field_validator("aggregation_functions")
    @classmethod
    def validate_aggregation_functions_supported(cls, v: list[str]) -> list[str]:
        """Validate that aggregation functions are supported."""
        supported_functions = {
            "sum",
            "count",
            "avg",
            "min",
            "max",
            "median",
            "std",
            "var",
            "percentile",
            "mode",
            "first",
            "last",
            "unique_count",
            # Infrastructure-specific functions
            "status_merge",
            "health_aggregate",
            "result_combine",
            # Statistical functions
            "skewness",
            "kurtosis",
            "correlation",
            "covariance",
        }

        for func in v:
            if func not in supported_functions:
                msg = f"Unsupported aggregation function: {func}"
                raise ValueError(msg)
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
