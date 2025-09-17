"""
Canary deployment configuration models.

Centralizes all configuration models for canary nodes including retry strategies,
circuit breaker configuration, metrics collection, and node configuration.
"""

import os
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# Enums for canary configuration
class RetryStrategyType(Enum):
    """Available retry strategy types."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"
    JITTERED_EXPONENTIAL = "jittered_exponential"


class RetryCondition(Enum):
    """Conditions that determine when to retry."""

    ANY_EXCEPTION = "any_exception"
    SPECIFIC_EXCEPTIONS = "specific_exceptions"
    HTTP_STATUS_CODES = "http_status_codes"
    CUSTOM_PREDICATE = "custom_predicate"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


# Configuration Models
class ModelRetryConfig(BaseModel):
    """Configuration for retry behavior."""

    strategy_type: RetryStrategyType = Field(
        default=RetryStrategyType.EXPONENTIAL,
        description="Type of retry strategy to use",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts",
    )
    base_delay_ms: int = Field(
        default=1000,
        ge=0,
        description="Base delay in milliseconds",
    )
    max_delay_ms: int = Field(
        default=30000,
        ge=1,
        description="Maximum delay between attempts in milliseconds",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Multiplier for exponential backoff",
    )
    jitter_enabled: bool = Field(
        default=True,
        description="Whether to add random jitter to delays",
    )
    jitter_max_ms: int = Field(
        default=1000,
        ge=0,
        description="Maximum jitter to add in milliseconds",
    )
    retry_condition: RetryCondition = Field(
        default=RetryCondition.ANY_EXCEPTION,
        description="Condition that determines when to retry",
    )
    retryable_exceptions: list[str] = Field(
        default_factory=lambda: [
            "ConnectionError",
            "TimeoutError",
            "asyncio.TimeoutError",
            "aiohttp.ClientError",
            "httpx.TimeoutException",
        ],
        description="List of exception class names that should trigger retries",
    )

    @field_validator("retryable_exceptions")
    def validate_exception_list(cls, v):
        """Validate that exception list is not empty when using specific exceptions."""
        if not v:
            raise ValueError("retryable_exceptions cannot be empty")
        return v


class ModelCircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening",
    )
    recovery_timeout_seconds: int = Field(
        default=60,
        description="Time before trying recovery",
    )
    success_threshold: int = Field(
        default=3,
        description="Successes needed to close from half-open",
    )
    timeout_seconds: float = Field(default=10.0, description="Request timeout")


class ModelCircuitBreakerStats(BaseModel):
    """Circuit breaker statistics."""

    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


class ModelMetricSummary(BaseModel):
    """Summary statistics for a metric."""

    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float


class ModelNodeMetrics(BaseModel):
    """Comprehensive metrics for a canary node."""

    # Operation metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Error metrics
    error_rate: float = 0.0
    timeout_count: int = 0
    circuit_breaker_trips: int = 0

    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Health metrics
    health_score: float = 1.0
    last_health_check: datetime | None = None

    # Custom metrics
    custom_metrics: dict[str, Any] = Field(default_factory=dict)


# Main Configuration Models
class ModelDatabaseConfig(BaseModel):
    """Database configuration for canary nodes."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="omnibase", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")

    def model_post_init(self, __context) -> None:
        """Validate database configuration after initialization."""
        # In production environments, require non-empty passwords
        is_production = self._is_production_environment()

        if is_production and not self.password:
            raise ValueError(
                "Database password is required in production environment. "
                "Set POSTGRES_PASSWORD environment variable.",
            )

        if is_production and self.password == "password":
            raise ValueError(
                "Default password 'password' is not allowed in production. "
                "Use a strong, unique password.",
            )

        # Validate password strength in production
        if is_production and len(self.password) < 8:
            raise ValueError(
                "Database password must be at least 8 characters long in production.",
            )

    def _is_production_environment(self) -> bool:
        """Check if we're in a production environment."""
        environment = os.getenv("ENVIRONMENT", "").lower()
        node_env = os.getenv("NODE_ENV", "").lower()

        return (
            environment in ["production", "prod"]
            or node_env in ["production", "prod"]
            or (
                os.getenv("DEBUG", "").lower() != "true"
                and os.getenv("DEV_MODE", "").lower() != "true"
            )
        )


class ModelTimeoutConfig(BaseModel):
    """Timeout configuration for various operations."""

    default_timeout_ms: int = Field(
        default=30000,
        description="Default timeout in milliseconds",
        ge=1000,
        le=300000,
    )
    gateway_timeout_ms: int = Field(
        default=10000,
        description="Gateway routing timeout",
        ge=1000,
        le=60000,
    )
    health_check_timeout_ms: int = Field(
        default=5000,
        description="Health check timeout",
        ge=500,
        le=30000,
    )
    api_call_timeout_ms: int = Field(
        default=10000,
        description="External API call timeout",
        ge=1000,
        le=120000,
    )
    workflow_step_timeout_ms: int = Field(
        default=60000,
        description="Workflow step timeout",
        ge=5000,
        le=600000,
    )


class ModelPerformanceConfig(BaseModel):
    """Performance and capacity configuration."""

    cache_max_size: int = Field(
        default=1000,
        description="Maximum cache entries",
        ge=10,
        le=100000,
    )
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds",
        ge=60,
        le=86400,
    )
    metrics_retention_count: int = Field(
        default=1000,
        description="Number of metrics to retain",
        ge=100,
        le=50000,
    )
    max_concurrent_operations: int = Field(
        default=100,
        description="Maximum concurrent operations",
        ge=1,
        le=10000,
    )
    error_rate_threshold: float = Field(
        default=0.1,
        description="Error rate threshold for health checks",
        ge=0.01,
        le=1.0,
    )
    min_operations_for_health: int = Field(
        default=10,
        description="Minimum operations before health evaluation",
        ge=1,
        le=1000,
    )


class ModelBusinessLogicConfig(BaseModel):
    """Business logic thresholds and parameters."""

    # Customer scoring
    customer_purchase_threshold: float = Field(
        default=1000.0,
        description="Customer purchase amount threshold",
    )
    customer_loyalty_years_threshold: int = Field(
        default=2,
        description="Customer loyalty years threshold",
    )
    customer_support_tickets_threshold: int = Field(
        default=3,
        description="Max support tickets for good score",
    )
    customer_premium_score_threshold: int = Field(
        default=30,
        description="Score threshold for premium tier",
    )
    customer_purchase_score_points: int = Field(
        default=20,
        description="Points for high purchase history",
    )
    customer_loyalty_score_points: int = Field(
        default=15,
        description="Points for loyalty",
    )
    customer_support_score_points: int = Field(
        default=10,
        description="Points for low support tickets",
    )

    # Health metrics
    health_score_excellent_threshold: float = Field(
        default=0.9,
        description="Health score threshold for excellent",
    )
    health_score_good_threshold: float = Field(
        default=0.6,
        description="Health score threshold for good/degraded",
    )

    # Canary deployment
    canary_error_rate_threshold: float = Field(
        default=0.05,
        description="Error rate threshold for canary promotion",
    )
    canary_default_traffic_percentage: int = Field(
        default=10,
        description="Default canary traffic percentage",
    )
    canary_test_duration_minutes: int = Field(
        default=15,
        description="Default canary test duration",
    )

    # Simulation delays (for testing)
    api_simulation_delay_ms: int = Field(
        default=100,
        description="API call simulation delay",
    )
    file_operation_delay_ms: int = Field(
        default=50,
        description="File operation simulation delay",
    )
    database_operation_delay_ms: int = Field(
        default=150,
        description="Database operation simulation delay",
    )
    queue_operation_delay_ms: int = Field(
        default=50,
        description="Queue operation simulation delay",
    )


class ModelSecurityConfig(BaseModel):
    """Security configuration for canary nodes."""

    log_sensitive_data: bool = Field(
        default=False,
        description="Whether to log sensitive data",
    )
    max_error_detail_length: int = Field(
        default=1000,
        description="Maximum error detail length in logs",
    )
    sanitize_stack_traces: bool = Field(
        default=True,
        description="Whether to sanitize stack traces in production",
    )
    correlation_id_validation: bool = Field(
        default=True,
        description="Whether to validate correlation IDs",
    )

    # Environment and debugging
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode with simulation delays",
    )

    # Correlation ID validation parameters
    correlation_id_min_length: int = Field(
        default=8,
        description="Minimum correlation ID length",
    )
    correlation_id_max_length: int = Field(
        default=128,
        description="Maximum correlation ID length",
    )

    # Connection pool limits
    max_connections_per_endpoint: int = Field(
        default=10,
        description="Maximum pooled connections per endpoint",
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Circuit breaker failure threshold",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        description="Circuit breaker recovery timeout in seconds",
    )

    # Enhanced security parameters
    mask_credentials_in_logs: bool = Field(
        default=True,
        description="Always mask credentials in log outputs",
    )
    mask_sensitive_headers: bool = Field(
        default=True,
        description="Mask sensitive HTTP headers in logs",
    )
    secure_error_responses: bool = Field(
        default=True,
        description="Sanitize error responses in production",
    )
    connection_string_logging: bool = Field(
        default=False,
        description="Enable connection string logging (dev only)",
    )

    def model_post_init(self, __context) -> None:
        """Validate security configuration after initialization."""
        is_production = self._is_production_environment()

        # Enforce security settings in production
        if is_production:
            if self.log_sensitive_data:
                raise ValueError("log_sensitive_data must be False in production")
            if self.connection_string_logging:
                raise ValueError(
                    "connection_string_logging must be False in production",
                )
            if not self.mask_credentials_in_logs:
                raise ValueError("mask_credentials_in_logs must be True in production")
            if not self.sanitize_stack_traces:
                raise ValueError("sanitize_stack_traces must be True in production")

    def _is_production_environment(self) -> bool:
        """Check if we're in a production environment."""
        import os

        environment = os.getenv("ENVIRONMENT", "").lower()
        node_env = os.getenv("NODE_ENV", "").lower()

        return (
            environment in ["production", "prod"]
            or node_env in ["production", "prod"]
            or (
                os.getenv("DEBUG", "").lower() != "true"
                and os.getenv("DEV_MODE", "").lower() != "true"
            )
        )


class ModelCanaryNodeConfig(BaseModel):
    """Complete configuration for canary nodes."""

    database: ModelDatabaseConfig = Field(default_factory=ModelDatabaseConfig)
    timeouts: ModelTimeoutConfig = Field(default_factory=ModelTimeoutConfig)
    performance: ModelPerformanceConfig = Field(default_factory=ModelPerformanceConfig)
    business_logic: ModelBusinessLogicConfig = Field(
        default_factory=ModelBusinessLogicConfig,
    )
    security: ModelSecurityConfig = Field(default_factory=ModelSecurityConfig)

    @classmethod
    def from_environment(cls) -> "ModelCanaryNodeConfig":
        """Create configuration from environment variables with fallback to defaults."""

        # Database config from environment
        database_config = ModelDatabaseConfig(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "omnibase"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_pool_size=int(os.getenv("DB_MIN_POOL_SIZE", "5")),
            max_pool_size=int(os.getenv("DB_MAX_POOL_SIZE", "20")),
        )

        # Timeout config from environment
        timeout_config = ModelTimeoutConfig(
            default_timeout_ms=int(os.getenv("DEFAULT_TIMEOUT_MS", "30000")),
            gateway_timeout_ms=int(os.getenv("GATEWAY_TIMEOUT_MS", "10000")),
            health_check_timeout_ms=int(os.getenv("HEALTH_CHECK_TIMEOUT_MS", "5000")),
            api_call_timeout_ms=int(os.getenv("API_CALL_TIMEOUT_MS", "10000")),
            workflow_step_timeout_ms=int(
                os.getenv("WORKFLOW_STEP_TIMEOUT_MS", "60000"),
            ),
        )

        # Performance config from environment
        performance_config = ModelPerformanceConfig(
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
            metrics_retention_count=int(os.getenv("METRICS_RETENTION_COUNT", "1000")),
            max_concurrent_operations=int(
                os.getenv("MAX_CONCURRENT_OPERATIONS", "100"),
            ),
            error_rate_threshold=float(os.getenv("ERROR_RATE_THRESHOLD", "0.1")),
            min_operations_for_health=int(os.getenv("MIN_OPERATIONS_FOR_HEALTH", "10")),
        )

        # Business logic config from environment
        business_logic_config = ModelBusinessLogicConfig(
            customer_purchase_threshold=float(
                os.getenv("CUSTOMER_PURCHASE_THRESHOLD", "1000.0"),
            ),
            customer_loyalty_years_threshold=int(
                os.getenv("CUSTOMER_LOYALTY_YEARS_THRESHOLD", "2"),
            ),
            customer_support_tickets_threshold=int(
                os.getenv("CUSTOMER_SUPPORT_TICKETS_THRESHOLD", "3"),
            ),
            customer_premium_score_threshold=int(
                os.getenv("CUSTOMER_PREMIUM_SCORE_THRESHOLD", "30"),
            ),
            canary_error_rate_threshold=float(
                os.getenv("CANARY_ERROR_RATE_THRESHOLD", "0.05"),
            ),
            canary_default_traffic_percentage=int(
                os.getenv("CANARY_DEFAULT_TRAFFIC_PERCENTAGE", "10"),
            ),
            canary_test_duration_minutes=int(
                os.getenv("CANARY_TEST_DURATION_MINUTES", "15"),
            ),
        )

        # Security config from environment
        security_config = ModelSecurityConfig(
            log_sensitive_data=os.getenv("LOG_SENSITIVE_DATA", "false").lower()
            == "true",
            max_error_detail_length=int(os.getenv("MAX_ERROR_DETAIL_LENGTH", "1000")),
            sanitize_stack_traces=os.getenv("SANITIZE_STACK_TRACES", "true").lower()
            == "true",
            correlation_id_validation=os.getenv(
                "CORRELATION_ID_VALIDATION",
                "true",
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
