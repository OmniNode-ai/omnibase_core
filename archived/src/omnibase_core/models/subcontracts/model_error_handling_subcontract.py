#!/usr/bin/env python3
"""
Error Handling Subcontract Model - Pydantic backing for mixin_error_handling.yaml

Provides comprehensive type safety and validation for the error handling mixin,
including secure error handling, circuit breakers, metrics collection, and
configuration management capabilities.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Type

from pydantic import BaseModel, Field, field_validator


class CircuitBreakerState(str, Enum):
    """Circuit breaker state enumeration."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ConfigurationSource(str, Enum):
    """Configuration data source enumeration."""

    ENVIRONMENT = "environment"
    DEFAULTS = "defaults"
    MIXED = "mixed"


class ConfigurationSection(str, Enum):
    """Available configuration sections."""

    DATABASE = "database"
    TIMEOUTS = "timeouts"
    PERFORMANCE = "performance"
    BUSINESS_LOGIC = "business_logic"
    SECURITY = "security"


# Action Input Models


class HandleErrorInput(BaseModel):
    """Input model for handle_error action."""

    error: Any = Field(..., description="Exception instance to handle")
    context: dict[str, Any] = Field(
        ...,
        description="Operation context (will be sanitized)",
    )
    correlation_id: str | None = Field(
        None,
        description="Request correlation ID for tracing",
    )
    operation_name: str = Field(..., description="Name of the operation that failed")

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str | None) -> str | None:
        """Validate correlation ID format."""
        if v is not None and (len(v) < 8 or len(v) > 128):
            raise ValueError("correlation_id must be between 8-128 characters")
        return v

    @field_validator("operation_name")
    @classmethod
    def validate_operation_name(cls, v: str) -> str:
        """Validate operation name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("operation_name cannot be empty")
        if len(v) > 100:
            raise ValueError("operation_name must be <= 100 characters")
        return v.strip()


class ModelCircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration model."""

    failure_threshold: int = Field(
        ...,
        ge=1,
        description="Number of failures before opening circuit",
    )
    recovery_timeout_seconds: float = Field(
        ...,
        ge=0.1,
        description="Time to wait before attempting recovery",
    )
    timeout_seconds: float = Field(
        ...,
        ge=0.1,
        description="Operation timeout threshold",
    )

    @field_validator("failure_threshold")
    @classmethod
    def validate_failure_threshold(cls, v: int) -> int:
        """Validate failure threshold is reasonable."""
        if v > 100:
            raise ValueError("failure_threshold should be <= 100 for practical use")
        return v


class CreateCircuitBreakerInput(BaseModel):
    """Input model for create_circuit_breaker action."""

    name: str = Field(..., description="Unique circuit breaker identifier")
    config: ModelCircuitBreakerConfig = Field(
        ...,
        description="Circuit breaker configuration",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate circuit breaker name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Circuit breaker name cannot be empty")
        if len(v) > 50:
            raise ValueError("Circuit breaker name must be <= 50 characters")
        return v.strip()


class RecordMetricsInput(BaseModel):
    """Input model for record_metrics action."""

    operation_name: str = Field(..., description="Name of the operation being measured")
    success: bool = Field(..., description="Whether the operation succeeded")
    duration_ms: float = Field(
        ...,
        ge=0,
        description="Operation duration in milliseconds",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Additional operation metadata",
    )

    @field_validator("operation_name")
    @classmethod
    def validate_operation_name(cls, v: str) -> str:
        """Validate operation name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("operation_name cannot be empty")
        return v.strip()

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        """Validate duration is reasonable."""
        if v > 300000:  # 5 minutes
            raise ValueError(
                "duration_ms should be <= 300000ms for practical monitoring",
            )
        return v


class GetConfigurationInput(BaseModel):
    """Input model for get_configuration action."""

    config_section: ConfigurationSection = Field(
        ...,
        description="Configuration section to retrieve",
    )


# Action Output Models


class HandleErrorOutput(BaseModel):
    """Output model for handle_error action."""

    message: str = Field(
        ...,
        description="Safe error message without sensitive information",
    )
    safe_context: dict[str, Any] = Field(
        ...,
        description="Sanitized context safe for logging",
    )
    error_id: str = Field(..., description="Unique identifier for error tracking")
    correlation_id: str | None = Field(None, description="Request correlation ID")

    @field_validator("error_id")
    @classmethod
    def validate_error_id(cls, v: str) -> str:
        """Ensure error ID is non-empty."""
        if not v:
            raise ValueError("error_id cannot be empty")
        return v


class CreateCircuitBreakerOutput(BaseModel):
    """Output model for create_circuit_breaker action."""

    circuit_breaker_id: str = Field(..., description="Circuit breaker identifier")
    state: CircuitBreakerState = Field(..., description="Initial circuit breaker state")


class RecordMetricsOutput(BaseModel):
    """Output model for record_metrics action."""

    recorded: bool = Field(
        ...,
        description="Whether metrics were successfully recorded",
    )
    operation_count: int = Field(
        ...,
        ge=0,
        description="Total operations recorded for this operation type",
    )
    error_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="Current error rate for this operation type",
    )


class GetConfigurationOutput(BaseModel):
    """Output model for get_configuration action."""

    config_data: dict[str, Any] = Field(..., description="Type-safe configuration data")
    source: ConfigurationSource = Field(..., description="Configuration data source")


# Mixin Output Models


class ErrorHandlingResult(BaseModel):
    """Result of secure error handling operation."""

    message: str = Field(..., description="Safe error message")
    error_id: str = Field(..., description="Unique error identifier")
    safe_context: dict[str, Any] | None = Field(
        None,
        description="Sanitized operation context",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Error occurrence timestamp",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is reasonable."""
        now = datetime.now(UTC)
        if v > now:
            # Future timestamps not allowed
            return now
        return v


class CircuitBreakerStateInfo(BaseModel):
    """Circuit breaker current state information."""

    name: str = Field(..., description="Circuit breaker identifier")
    state: CircuitBreakerState = Field(..., description="Current circuit breaker state")
    failure_count: int = Field(
        ...,
        ge=0,
        description="Current consecutive failure count",
    )
    last_failure_time: datetime | None = Field(
        None,
        description="Timestamp of last failure",
    )
    success_count: int = Field(..., ge=0, description="Total successful operations")

    @field_validator("failure_count", "success_count")
    @classmethod
    def validate_counts(cls, v: int) -> int:
        """Validate count fields are non-negative."""
        if v < 0:
            raise ValueError("Count fields cannot be negative")
        return v


class MetricsSnapshot(BaseModel):
    """Performance metrics snapshot."""

    operation_name: str = Field(..., description="Operation being measured")
    total_count: int = Field(..., ge=0, description="Total operation count")
    success_count: int = Field(..., ge=0, description="Successful operation count")
    error_count: int = Field(..., ge=0, description="Failed operation count")
    success_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="Success rate (0.0 to 1.0)",
    )
    avg_duration_ms: float = Field(..., ge=0, description="Average operation duration")
    percentiles: dict[str, float] = Field(
        default_factory=dict,
        description="Performance percentile calculations",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last metrics update timestamp",
    )

    @field_validator("success_rate")
    @classmethod
    def validate_success_rate(cls, v: float) -> float:
        """Validate success rate is between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("success_rate must be between 0.0 and 1.0")
        return v

    @field_validator("total_count", "success_count", "error_count")
    @classmethod
    def validate_counts(cls, v: int) -> int:
        """Validate count fields are non-negative."""
        if v < 0:
            raise ValueError("Count fields cannot be negative")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate count consistency."""
        if self.success_count + self.error_count > self.total_count:
            raise ValueError("success_count + error_count cannot exceed total_count")


# Configuration Models


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration section."""

    sanitize_production_errors: bool = Field(
        True,
        description="Enable sensitive data sanitization in production",
    )
    max_context_fields: int = Field(
        20,
        ge=1,
        description="Maximum context fields to include in error details",
    )
    correlation_id_required: bool = Field(
        False,
        description="Whether correlation ID is required for all operations",
    )


class CircuitBreakersConfig(BaseModel):
    """Circuit breakers configuration section."""

    default_failure_threshold: int = Field(
        5,
        ge=1,
        description="Default failure threshold for circuit breakers",
    )
    default_recovery_timeout: float = Field(
        30.0,
        ge=0.1,
        description="Default recovery timeout in seconds",
    )
    default_operation_timeout: float = Field(
        10.0,
        ge=0.1,
        description="Default operation timeout in seconds",
    )


class MetricsConfig(BaseModel):
    """Metrics configuration section."""

    enable_detailed_metrics: bool = Field(
        True,
        description="Enable detailed performance metrics collection",
    )
    metrics_retention_count: int = Field(
        1000,
        ge=100,
        description="Number of metric entries to retain in memory",
    )
    percentile_calculations: list[float] = Field(
        default=[50, 95, 99],
        description="Percentiles to calculate for performance metrics",
    )

    @field_validator("percentile_calculations")
    @classmethod
    def validate_percentiles(cls, v: list[float]) -> list[float]:
        """Validate percentile values are between 0 and 100."""
        for percentile in v:
            if not (0 <= percentile <= 100):
                raise ValueError("Percentiles must be between 0 and 100")
        return sorted(set(v))  # Remove duplicates and sort


# Main Subcontract Model


class ModelErrorHandlingSubcontract(BaseModel):
    """
    Complete error handling subcontract model providing type safety for all
    error handling mixin capabilities including secure error handling,
    circuit breakers, metrics collection, and configuration management.
    """

    # Configuration sections
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)
    circuit_breakers: CircuitBreakersConfig = Field(
        default_factory=CircuitBreakersConfig,
    )
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    # Capability flags
    secure_error_handling_enabled: bool = Field(
        True,
        description="Enable secure error handling capability",
    )
    circuit_breaker_management_enabled: bool = Field(
        True,
        description="Enable circuit breaker management capability",
    )
    metrics_collection_enabled: bool = Field(
        True,
        description="Enable metrics collection capability",
    )
    configuration_management_enabled: bool = Field(
        True,
        description="Enable configuration management capability",
    )

    # Operational state
    initialized: bool = Field(
        False,
        description="Whether the error handling mixin has been initialized",
    )
    initialization_timestamp: datetime | None = Field(
        None,
        description="When initialization completed",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Prevent additional fields

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation."""
        # Validate at least one capability is enabled
        if not any(
            [
                self.secure_error_handling_enabled,
                self.circuit_breaker_management_enabled,
                self.metrics_collection_enabled,
                self.configuration_management_enabled,
            ],
        ):
            raise ValueError("At least one error handling capability must be enabled")

        # Set initialization timestamp if not already set
        if self.initialized and self.initialization_timestamp is None:
            object.__setattr__(
                self,
                "initialization_timestamp",
                datetime.now(UTC),
            )

    def get_enabled_capabilities(self) -> list[str]:
        """Get list of enabled capabilities."""
        capabilities = []
        if self.secure_error_handling_enabled:
            capabilities.append("secure_error_handling")
        if self.circuit_breaker_management_enabled:
            capabilities.append("circuit_breaker_management")
        if self.metrics_collection_enabled:
            capabilities.append("metrics_collection")
        if self.configuration_management_enabled:
            capabilities.append("configuration_management")
        return capabilities

    def validate_action_input(
        self,
        action: str,
        input_data: dict[str, Any],
    ) -> BaseModel:
        """Validate and parse action input data."""
        action_input_models: dict[str, Type[BaseModel]] = {
            "handle_error": HandleErrorInput,
            "create_circuit_breaker": CreateCircuitBreakerInput,
            "record_metrics": RecordMetricsInput,
            "get_configuration": GetConfigurationInput,
        }

        if action not in action_input_models:
            raise ValueError(f"Unknown action: {action}")

        model_class = action_input_models[action]
        return model_class.model_validate(input_data)

    def create_action_output(
        self,
        action: str,
        output_data: dict[str, Any],
    ) -> BaseModel:
        """Create and validate action output data."""
        action_output_models: dict[str, Type[BaseModel]] = {
            "handle_error": HandleErrorOutput,
            "create_circuit_breaker": CreateCircuitBreakerOutput,
            "record_metrics": RecordMetricsOutput,
            "get_configuration": GetConfigurationOutput,
        }

        if action not in action_output_models:
            raise ValueError(f"Unknown action: {action}")

        model_class = action_output_models[action]
        return model_class.model_validate(output_data)


# Utility functions for mixin integration


def create_error_handling_subcontract(**kwargs) -> ModelErrorHandlingSubcontract:
    """Create a new error handling subcontract instance with validation."""
    return ModelErrorHandlingSubcontract(**kwargs)


def get_default_error_handling_config() -> dict[str, Any]:
    """Get default configuration for error handling mixin."""
    return {
        "error_handling": ErrorHandlingConfig().model_dump(),
        "circuit_breakers": CircuitBreakersConfig().model_dump(),
        "metrics": MetricsConfig().model_dump(),
        "secure_error_handling_enabled": True,
        "circuit_breaker_management_enabled": True,
        "metrics_collection_enabled": True,
        "configuration_management_enabled": True,
    }


# Export all public models and functions
__all__ = [
    # Enums
    "CircuitBreakerState",
    "ConfigurationSource",
    "ConfigurationSection",
    # Action Input Models
    "HandleErrorInput",
    "CreateCircuitBreakerInput",
    "RecordMetricsInput",
    "GetConfigurationInput",
    # Action Output Models
    "HandleErrorOutput",
    "CreateCircuitBreakerOutput",
    "RecordMetricsOutput",
    "GetConfigurationOutput",
    # Mixin Output Models
    "ErrorHandlingResult",
    "CircuitBreakerStateInfo",
    "MetricsSnapshot",
    # Configuration Models
    "ErrorHandlingConfig",
    "CircuitBreakersConfig",
    "MetricsConfig",
    # Main Subcontract Model
    "ModelErrorHandlingSubcontract",
    # Utility Functions
    "create_error_handling_subcontract",
    "get_default_error_handling_config",
]
