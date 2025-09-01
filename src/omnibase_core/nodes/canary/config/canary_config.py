#!/usr/bin/env python3
"""
Configuration management for canary nodes.

Centralizes all configuration values that were previously hardcoded,
providing environment-based configuration with sensible defaults.
"""

import os
from typing import Any, Dict

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration for canary nodes."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="omnibase", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")


class TimeoutConfig(BaseModel):
    """Timeout configuration for various operations."""

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


class PerformanceConfig(BaseModel):
    """Performance and capacity configuration."""

    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    metrics_retention_count: int = Field(
        default=1000, description="Number of metrics to retain"
    )
    max_concurrent_operations: int = Field(
        default=100, description="Maximum concurrent operations"
    )
    error_rate_threshold: float = Field(
        default=0.1, description="Error rate threshold for health checks"
    )
    min_operations_for_health: int = Field(
        default=10, description="Minimum operations before health evaluation"
    )


class BusinessLogicConfig(BaseModel):
    """Business logic thresholds and parameters."""

    # Customer scoring
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

    # Health metrics
    health_score_excellent_threshold: float = Field(
        default=0.9, description="Health score threshold for excellent"
    )
    health_score_good_threshold: float = Field(
        default=0.6, description="Health score threshold for good/degraded"
    )

    # Canary deployment
    canary_error_rate_threshold: float = Field(
        default=0.05, description="Error rate threshold for canary promotion"
    )
    canary_default_traffic_percentage: int = Field(
        default=10, description="Default canary traffic percentage"
    )
    canary_test_duration_minutes: int = Field(
        default=15, description="Default canary test duration"
    )

    # Simulation delays (for testing)
    api_simulation_delay_ms: int = Field(
        default=100, description="API call simulation delay"
    )
    file_operation_delay_ms: int = Field(
        default=50, description="File operation simulation delay"
    )
    database_operation_delay_ms: int = Field(
        default=150, description="Database operation simulation delay"
    )
    queue_operation_delay_ms: int = Field(
        default=50, description="Queue operation simulation delay"
    )


class SecurityConfig(BaseModel):
    """Security configuration for canary nodes."""

    log_sensitive_data: bool = Field(
        default=False, description="Whether to log sensitive data"
    )
    max_error_detail_length: int = Field(
        default=1000, description="Maximum error detail length in logs"
    )
    sanitize_stack_traces: bool = Field(
        default=True, description="Whether to sanitize stack traces in production"
    )
    correlation_id_validation: bool = Field(
        default=True, description="Whether to validate correlation IDs"
    )


class CanaryNodeConfig(BaseModel):
    """Complete configuration for canary nodes."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    business_logic: BusinessLogicConfig = Field(default_factory=BusinessLogicConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @classmethod
    def from_environment(cls) -> "CanaryNodeConfig":
        """Create configuration from environment variables with fallback to defaults."""

        # Database config from environment
        database_config = DatabaseConfig(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "omnibase"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_pool_size=int(os.getenv("DB_MIN_POOL_SIZE", "5")),
            max_pool_size=int(os.getenv("DB_MAX_POOL_SIZE", "20")),
        )

        # Timeout config from environment
        timeout_config = TimeoutConfig(
            default_timeout_ms=int(os.getenv("DEFAULT_TIMEOUT_MS", "30000")),
            gateway_timeout_ms=int(os.getenv("GATEWAY_TIMEOUT_MS", "10000")),
            health_check_timeout_ms=int(os.getenv("HEALTH_CHECK_TIMEOUT_MS", "5000")),
            api_call_timeout_ms=int(os.getenv("API_CALL_TIMEOUT_MS", "10000")),
            workflow_step_timeout_ms=int(
                os.getenv("WORKFLOW_STEP_TIMEOUT_MS", "60000")
            ),
        )

        # Performance config from environment
        performance_config = PerformanceConfig(
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
            metrics_retention_count=int(os.getenv("METRICS_RETENTION_COUNT", "1000")),
            max_concurrent_operations=int(
                os.getenv("MAX_CONCURRENT_OPERATIONS", "100")
            ),
            error_rate_threshold=float(os.getenv("ERROR_RATE_THRESHOLD", "0.1")),
            min_operations_for_health=int(os.getenv("MIN_OPERATIONS_FOR_HEALTH", "10")),
        )

        # Business logic config from environment
        business_logic_config = BusinessLogicConfig(
            customer_purchase_threshold=float(
                os.getenv("CUSTOMER_PURCHASE_THRESHOLD", "1000.0")
            ),
            customer_loyalty_years_threshold=int(
                os.getenv("CUSTOMER_LOYALTY_YEARS_THRESHOLD", "2")
            ),
            customer_support_tickets_threshold=int(
                os.getenv("CUSTOMER_SUPPORT_TICKETS_THRESHOLD", "3")
            ),
            customer_premium_score_threshold=int(
                os.getenv("CUSTOMER_PREMIUM_SCORE_THRESHOLD", "30")
            ),
            canary_error_rate_threshold=float(
                os.getenv("CANARY_ERROR_RATE_THRESHOLD", "0.05")
            ),
            canary_default_traffic_percentage=int(
                os.getenv("CANARY_DEFAULT_TRAFFIC_PERCENTAGE", "10")
            ),
            canary_test_duration_minutes=int(
                os.getenv("CANARY_TEST_DURATION_MINUTES", "15")
            ),
        )

        # Security config from environment
        security_config = SecurityConfig(
            log_sensitive_data=os.getenv("LOG_SENSITIVE_DATA", "false").lower()
            == "true",
            max_error_detail_length=int(os.getenv("MAX_ERROR_DETAIL_LENGTH", "1000")),
            sanitize_stack_traces=os.getenv("SANITIZE_STACK_TRACES", "true").lower()
            == "true",
            correlation_id_validation=os.getenv(
                "CORRELATION_ID_VALIDATION", "true"
            ).lower()
            == "true",
        )

        return cls(
            database=database_config,
            timeouts=timeout_config,
            performance=performance_config,
            business_logic=business_logic_config,
            security=security_config,
        )


# Global config instance
_config_instance: CanaryNodeConfig | None = None


def get_canary_config() -> CanaryNodeConfig:
    """Get the global canary node configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = CanaryNodeConfig.from_environment()
    return _config_instance


def reload_config() -> CanaryNodeConfig:
    """Reload configuration from environment (useful for tests)."""
    global _config_instance
    _config_instance = CanaryNodeConfig.from_environment()
    return _config_instance
