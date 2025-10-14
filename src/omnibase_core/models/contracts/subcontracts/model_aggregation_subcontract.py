"""
Aggregation Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION
STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

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

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.metadata.model_semver import ModelSemVer

from .model_aggregation_function import ModelAggregationFunction
from .model_aggregation_performance import ModelAggregationPerformance
from .model_data_grouping import ModelDataGrouping
from .model_statistical_computation import ModelStatisticalComputation
from .model_windowing_strategy import ModelWindowingStrategy


class ModelAggregationSubcontract(BaseModel):
    """
    Aggregation subcontract model for data aggregation functionality.

    Comprehensive aggregation subcontract providing aggregation functions,
    grouping strategies, windowing, and statistical computations.
    Designed for composition into node contracts requiring aggregation functionality.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

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
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return v

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
