"""
Circuit Breaker Subcontract Model.



Dedicated subcontract model for circuit breaker functionality providing:
- Failure threshold monitoring with automatic circuit opening
- Half-open state for service recovery testing
- Configurable timeout and success thresholds
- Integration with retry patterns for comprehensive resilience
- Sliding window failure rate detection

This model is composed into node contracts that require circuit breaker functionality,
providing clean separation between node logic and resilience behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCircuitBreakerSubcontract(BaseModel):
    """
    Circuit breaker subcontract model for fault tolerance.

    Comprehensive circuit breaker configuration implementing the circuit breaker
    pattern to prevent cascade failures by monitoring node health and temporarily
    disabling failing operations following ONEX standards.

    Circuit States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing state, requests blocked immediately
    - HALF_OPEN: Testing recovery, limited requests allowed

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

    # Core circuit breaker configuration
    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of consecutive failures before opening circuit",
    )

    half_open_max_calls: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of calls allowed in half-open state",
    )

    success_threshold: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Number of consecutive successes to close circuit from half-open",
    )

    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout duration before attempting to close circuit (open → half-open)",
    )

    # Advanced configuration
    window_size_seconds: int = Field(
        default=120,
        ge=30,
        le=3600,
        description="Time window for failure rate calculation (sliding window)",
    )

    failure_rate_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Failure rate threshold (0.0-1.0) to open circuit",
    )

    minimum_request_threshold: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Minimum requests before failure rate is considered",
    )

    # Slow call detection
    slow_call_duration_threshold_ms: int | None = Field(
        default=None,
        ge=100,
        le=60000,
        description="Duration threshold for slow calls in milliseconds (None = disabled)",
    )

    slow_call_rate_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Slow call rate threshold (0.0-1.0) to open circuit (None = disabled)",
    )

    # Integration flags
    automatic_transition_enabled: bool = Field(
        default=True,
        description="Whether automatic state transitions are enabled",
    )

    event_logging_enabled: bool = Field(
        default=True,
        description="Whether circuit breaker state changes are logged",
    )

    metrics_tracking_enabled: bool = Field(
        default=True,
        description="Whether detailed metrics tracking is enabled",
    )

    # Fallback configuration
    fallback_enabled: bool = Field(
        default=False,
        description="Whether fallback mechanism is enabled when circuit is open",
    )

    ignore_exceptions: list[str] = Field(
        default_factory=list,
        description="List of exception types to ignore (not counted as failures)",
    )

    record_exceptions: list[str] = Field(
        default_factory=lambda: [
            "timeout",
            "connection_error",
            "service_unavailable",
            "internal_error",
        ],
        description="List of exception types to record as failures",
    )

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_seconds(cls, v: int) -> int:
        """Validate timeout is reasonable for production use."""
        if v < 10:
            msg = f"timeout_seconds ({v}) is too short for production use (minimum 10 seconds recommended)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "field_validation",
                        ),
                        "field": ModelSchemaValue.from_value("timeout_seconds"),
                    },
                ),
            )
        return v

    @field_validator("failure_rate_threshold")
    @classmethod
    def validate_failure_rate_threshold(cls, v: float) -> float:
        """Validate failure rate threshold is reasonable."""
        if v < 0.1:
            msg = f"failure_rate_threshold ({v}) is very aggressive, may cause false positives (minimum 0.1 recommended)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "field_validation",
                        ),
                        "field": ModelSchemaValue.from_value("failure_rate_threshold"),
                    },
                ),
            )
        return v

    @model_validator(mode="after")
    def validate_threshold_relationships(self) -> Self:
        """Validate cross-field threshold and timing relationships."""
        # Validate success_threshold <= half_open_max_calls
        if self.success_threshold > self.half_open_max_calls:
            msg = f"success_threshold ({self.success_threshold}) cannot exceed half_open_max_calls ({self.half_open_max_calls})"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("success_threshold"),
                        "success_threshold": ModelSchemaValue.from_value(
                            self.success_threshold
                        ),
                        "half_open_max_calls": ModelSchemaValue.from_value(
                            self.half_open_max_calls
                        ),
                    },
                ),
            )

        # Validate window_size_seconds >= timeout_seconds
        if self.window_size_seconds < self.timeout_seconds:
            msg = f"window_size_seconds ({self.window_size_seconds}) should be >= timeout_seconds ({self.timeout_seconds}) for accurate failure rate calculation"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("window_size_seconds"),
                        "window_size": ModelSchemaValue.from_value(
                            self.window_size_seconds
                        ),
                        "timeout": ModelSchemaValue.from_value(self.timeout_seconds),
                    },
                ),
            )

        # Validate slow_call_rate requires slow_call_duration
        if (
            self.slow_call_rate_threshold is not None
            and self.slow_call_duration_threshold_ms is None
        ):
            msg = "slow_call_rate_threshold requires slow_call_duration_threshold_ms to be set"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "slow_call_rate_threshold"
                        ),
                    },
                ),
            )

        # Validate minimum_request_threshold >= 2x failure_threshold
        if self.minimum_request_threshold < self.failure_threshold * 2:
            msg = f"minimum_request_threshold ({self.minimum_request_threshold}) should be at least 2x failure_threshold ({self.failure_threshold}) for statistical significance"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "minimum_request_threshold"
                        ),
                        "minimum_threshold": ModelSchemaValue.from_value(
                            self.minimum_request_threshold
                        ),
                        "failure_threshold": ModelSchemaValue.from_value(
                            self.failure_threshold
                        ),
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on attribute assignment
    )
