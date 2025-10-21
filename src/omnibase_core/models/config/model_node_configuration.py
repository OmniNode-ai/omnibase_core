import os
from typing import Any, Optional

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

from .model_business_logic_config import ModelBusinessLogicConfig
from .model_performance_config import ModelPerformanceConfig
from .model_security_config import ModelSecurityConfig
from .model_timeout_config import ModelTimeoutConfig


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

    def get_config_value(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value by dot-separated key path."""
        parts = key.split(".")
        current = self.model_dump()

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                if default is not None:
                    return default
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                    message=f"Configuration key '{key}' not found",
                )

        return current

    def get_timeout_ms(self, timeout_type: str, default_ms: int = 30000) -> int:
        """Get timeout configuration in milliseconds."""
        return getattr(self.timeouts, f"{timeout_type}_timeout_ms", default_ms)

    def get_security_config(self, key: str, default: Optional[Any] = None) -> Any:
        """Get security-related configuration value."""
        return getattr(self.security, key, default)

    def get_business_logic_config(self, key: str, default: Optional[Any] = None) -> Any:
        """Get business logic configuration value."""
        return getattr(self.business_logic, key, default)

    def get_performance_config(self, key: str, default: Optional[Any] = None) -> Any:
        """Get performance-related configuration value."""
        return getattr(self.performance, key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        try:
            self.get_config_value(key)
            return True
        except KeyError:
            return False

    def get_all_config(self) -> dict[str, Any]:
        """Get all configuration as dictionary."""
        return self.model_dump()
