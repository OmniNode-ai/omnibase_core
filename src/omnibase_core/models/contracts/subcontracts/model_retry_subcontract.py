"""
Retry Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

Dedicated subcontract model for retry logic providing:
- Configurable retry attempts with intelligent backoff strategies
- Exponential, linear, and constant backoff algorithms
- Jitter support for distributed systems
- Maximum delay caps to prevent excessive waiting
- Integration with circuit breaker patterns

This model is composed into node contracts that require retry functionality,
providing clean separation between node logic and retry behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.primitives.model_semver import ModelSemVer


class ModelRetrySubcontract(BaseModel):
    """
    Retry subcontract model for resilient operation execution.

    Comprehensive retry configuration providing intelligent backoff strategies,
    jitter support, and circuit breaker integration for handling failures
    in distributed operations following ONEX standards.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Core retry configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        le=100,
        description="Maximum number of retry attempts (0 = no retries)",
    )

    base_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=3600.0,
        description="Base delay between retries in seconds",
    )

    backoff_strategy: str = Field(
        default="exponential",
        description="Backoff strategy: exponential, linear, or constant",
    )

    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Multiplier for exponential backoff (ignored for constant/linear)",
    )

    max_delay_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=3600.0,
        description="Maximum delay cap in seconds to prevent excessive waiting",
    )

    jitter_enabled: bool = Field(
        default=True,
        description="Add random jitter to delays to prevent thundering herd",
    )

    jitter_factor: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Jitter factor as percentage of delay (0.1 = ±10%)",
    )

    # Error classification
    retryable_error_codes: list[str] = Field(
        default_factory=lambda: [
            "timeout",
            "network_error",
            "service_unavailable",
            "rate_limit",
            "temporary_failure",
        ],
        description="List of error codes that should trigger retry",
    )

    non_retryable_error_codes: list[str] = Field(
        default_factory=lambda: [
            "authentication_error",
            "authorization_error",
            "not_found",
            "validation_error",
            "bad_request",
        ],
        description="List of error codes that should NOT trigger retry",
    )

    # Circuit breaker integration
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether circuit breaker integration is enabled",
    )

    # Advanced configuration
    timeout_per_attempt_seconds: float | None = Field(
        default=None,
        ge=0.1,
        le=3600.0,
        description="Timeout for each individual retry attempt (None = no timeout)",
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry when individual attempts timeout",
    )

    exponential_cap_enabled: bool = Field(
        default=True,
        description="Whether to cap exponential growth at max_delay_seconds",
    )

    @field_validator("backoff_strategy")
    @classmethod
    def validate_backoff_strategy(cls, v: str) -> str:
        """Validate backoff strategy is one of the allowed values."""
        allowed_strategies = ["exponential", "linear", "constant"]
        if v not in allowed_strategies:
            msg = f"backoff_strategy must be one of {allowed_strategies}, got '{v}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "field_validation",
                        ),
                        "field": ModelSchemaValue.from_value("backoff_strategy"),
                        "allowed_values": ModelSchemaValue.from_value(
                            allowed_strategies
                        ),
                    },
                ),
            )
        return v

    @field_validator("jitter_factor")
    @classmethod
    def validate_jitter_factor(cls, v: float) -> float:
        """Validate jitter factor is reasonable for distributed systems."""
        if v > 0.5:
            msg = f"jitter_factor ({v}) should not exceed 0.5 (50%) for predictable behavior"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "field_validation",
                        ),
                        "field": ModelSchemaValue.from_value("jitter_factor"),
                    },
                ),
            )
        return v

    @model_validator(mode="after")
    def validate_delay_relationships(self) -> Self:
        """Validate cross-field delay relationships."""
        # Validate max_delay_seconds >= base_delay_seconds
        if self.max_delay_seconds < self.base_delay_seconds:
            msg = f"max_delay_seconds ({self.max_delay_seconds}) must be >= base_delay_seconds ({self.base_delay_seconds})"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("max_delay_seconds"),
                        "max_delay": ModelSchemaValue.from_value(
                            self.max_delay_seconds
                        ),
                        "base_delay": ModelSchemaValue.from_value(
                            self.base_delay_seconds
                        ),
                    },
                ),
            )

        # Validate timeout_per_attempt <= 2x max_delay_seconds
        if (
            self.timeout_per_attempt_seconds is not None
            and self.timeout_per_attempt_seconds > self.max_delay_seconds * 2
        ):
            msg = f"timeout_per_attempt_seconds ({self.timeout_per_attempt_seconds}) should not exceed 2x max_delay_seconds ({self.max_delay_seconds})"
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
                            "timeout_per_attempt_seconds"
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
