"""
Node configuration models using Pydantic for validation.

Provides strongly-typed configuration models that can be injected
via ModelONEXContainer following our architecture patterns.
"""

import os
from typing import Dict, Optional

from omnibase_spi.protocols.core import ProtocolNodeConfiguration
from omnibase_spi.protocols.types.core_types import ContextValue
from pydantic import BaseModel, Field


class ModelSecurityConfig(BaseModel):
    """Security configuration model."""

    log_sensitive_data: bool = Field(
        default=False, description="Whether to log sensitive data"
    )
    max_error_detail_length: int = Field(
        default=1000, description="Maximum error detail length"
    )
    sanitize_stack_traces: bool = Field(
        default=True, description="Sanitize stack traces in production"
    )
    correlation_id_validation: bool = Field(
        default=True, description="Enable correlation ID validation"
    )
    correlation_id_min_length: int = Field(
        default=8, description="Minimum correlation ID length"
    )
    correlation_id_max_length: int = Field(
        default=128, description="Maximum correlation ID length"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Circuit breaker failure threshold"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, description="Circuit breaker recovery timeout"
    )
    max_connections_per_endpoint: int = Field(
        default=10, description="Max pooled connections per endpoint"
    )


class ModelTimeoutConfig(BaseModel):
    """Timeout configuration model."""

    default_timeout_ms: int = Field(
        default=30000, description="Default timeout in milliseconds"
    )
    gateway_timeout_ms: int = Field(
        default=10000, description="Gateway routing timeout"
    )
    health_check_timeout_ms: int = Field(
        default=5000, description="Health check timeout"
    )
    api_call_timeout_ms: int = Field(
        default=10000, description="External API call timeout"
    )
    workflow_step_timeout_ms: int = Field(
        default=60000, description="Workflow step timeout"
    )


class ModelPerformanceConfig(BaseModel):
    """Performance configuration model."""

    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    max_concurrent_operations: int = Field(
        default=100, description="Maximum concurrent operations"
    )
    error_rate_threshold: float = Field(
        default=0.1, description="Error rate threshold for health"
    )
    min_operations_for_health: int = Field(
        default=10, description="Min operations before health evaluation"
    )
    health_score_threshold_good: float = Field(
        default=0.6, description="Health score threshold for good status"
    )


class ModelBusinessLogicConfig(BaseModel):
    """Business logic configuration model."""

    customer_purchase_threshold: float = Field(
        default=1000.0, description="Customer purchase amount threshold"
    )
    customer_loyalty_years_threshold: int = Field(
        default=2, description="Customer loyalty years threshold"
    )
    customer_support_tickets_threshold: int = Field(
        default=3, description="Max support tickets for good score"
    )
    customer_premium_score_threshold: int = Field(
        default=30, description="Score threshold for premium tier"
    )
    customer_purchase_score_points: int = Field(
        default=20, description="Points for high purchase history"
    )
    customer_loyalty_score_points: int = Field(
        default=15, description="Points for loyalty"
    )
    customer_support_score_points: int = Field(
        default=10, description="Points for low support tickets"
    )


class ModelNodeConfiguration(BaseModel):
    """
    Complete node configuration model.

    Strongly-typed configuration that implements ProtocolNodeConfiguration
    and can be injected via ModelONEXContainer.
    """

    security: ModelSecurityConfig = Field(default_factory=ModelSecurityConfig)
    timeouts: ModelTimeoutConfig = Field(default_factory=ModelTimeoutConfig)
    performance: ModelPerformanceConfig = Field(default_factory=ModelPerformanceConfig)
    business_logic: ModelBusinessLogicConfig = Field(
        default_factory=ModelBusinessLogicConfig
    )

    @classmethod
    def from_environment(cls) -> "ModelNodeConfiguration":
        """Create configuration from environment variables with fallback to defaults."""

        def get_env_bool(key: str, default: bool) -> bool:
            return os.getenv(key, str(default)).lower() == "true"

        def get_env_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        def get_env_float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                return default

        return cls(
            security=ModelSecurityConfig(
                log_sensitive_data=get_env_bool("LOG_SENSITIVE_DATA", False),
                max_error_detail_length=get_env_int("MAX_ERROR_DETAIL_LENGTH", 1000),
                sanitize_stack_traces=get_env_bool("SANITIZE_STACK_TRACES", True),
                correlation_id_validation=get_env_bool(
                    "CORRELATION_ID_VALIDATION", True
                ),
                correlation_id_min_length=get_env_int("CORRELATION_ID_MIN_LENGTH", 8),
                correlation_id_max_length=get_env_int("CORRELATION_ID_MAX_LENGTH", 128),
                circuit_breaker_failure_threshold=get_env_int(
                    "CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5
                ),
                circuit_breaker_recovery_timeout=get_env_int(
                    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT", 60
                ),
                max_connections_per_endpoint=get_env_int(
                    "MAX_CONNECTIONS_PER_ENDPOINT", 10
                ),
            ),
            timeouts=ModelTimeoutConfig(
                default_timeout_ms=get_env_int("DEFAULT_TIMEOUT_MS", 30000),
                gateway_timeout_ms=get_env_int("GATEWAY_TIMEOUT_MS", 10000),
                health_check_timeout_ms=get_env_int("HEALTH_CHECK_TIMEOUT_MS", 5000),
                api_call_timeout_ms=get_env_int("API_CALL_TIMEOUT_MS", 10000),
                workflow_step_timeout_ms=get_env_int("WORKFLOW_STEP_TIMEOUT_MS", 60000),
            ),
            performance=ModelPerformanceConfig(
                cache_max_size=get_env_int("CACHE_MAX_SIZE", 1000),
                cache_ttl_seconds=get_env_int("CACHE_TTL_SECONDS", 300),
                max_concurrent_operations=get_env_int("MAX_CONCURRENT_OPERATIONS", 100),
                error_rate_threshold=get_env_float("ERROR_RATE_THRESHOLD", 0.1),
                min_operations_for_health=get_env_int("MIN_OPERATIONS_FOR_HEALTH", 10),
                health_score_threshold_good=get_env_float(
                    "HEALTH_SCORE_THRESHOLD_GOOD", 0.6
                ),
            ),
            business_logic=ModelBusinessLogicConfig(
                customer_purchase_threshold=get_env_float(
                    "CUSTOMER_PURCHASE_THRESHOLD", 1000.0
                ),
                customer_loyalty_years_threshold=get_env_int(
                    "CUSTOMER_LOYALTY_YEARS_THRESHOLD", 2
                ),
                customer_support_tickets_threshold=get_env_int(
                    "CUSTOMER_SUPPORT_TICKETS_THRESHOLD", 3
                ),
                customer_premium_score_threshold=get_env_int(
                    "CUSTOMER_PREMIUM_SCORE_THRESHOLD", 30
                ),
                customer_purchase_score_points=get_env_int(
                    "CUSTOMER_PURCHASE_SCORE_POINTS", 20
                ),
                customer_loyalty_score_points=get_env_int(
                    "CUSTOMER_LOYALTY_SCORE_POINTS", 15
                ),
                customer_support_score_points=get_env_int(
                    "CUSTOMER_SUPPORT_SCORE_POINTS", 10
                ),
            ),
        )

    def get_config_value(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get configuration value by dot-separated key path."""
        parts = key.split(".")
        current = self.model_dump()

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                if default is not None:
                    return default
                raise KeyError(f"Configuration key '{key}' not found")

        return current

    def get_timeout_ms(self, timeout_type: str, default_ms: int = 30000) -> int:
        """Get timeout configuration in milliseconds."""
        return getattr(self.timeouts, f"{timeout_type}_timeout_ms", default_ms)

    def get_security_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get security-related configuration value."""
        return getattr(self.security, key, default)

    def get_business_logic_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get business logic configuration value."""
        return getattr(self.business_logic, key, default)

    def get_performance_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get performance-related configuration value."""
        return getattr(self.performance, key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        try:
            self.get_config_value(key)
            return True
        except KeyError:
            return False

    def get_all_config(self) -> Dict[str, ContextValue]:
        """Get all configuration as dictionary."""
        return self.model_dump()
