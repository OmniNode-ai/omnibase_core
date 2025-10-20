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
