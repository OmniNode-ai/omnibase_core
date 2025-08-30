#!/usr/bin/env python3
"""
Effect Contract Model - ONEX Standards Compliant.

Specialized contract model for NodeEffect implementations providing:
- I/O operation specifications (file, database, API endpoints)
- Transaction management configuration
- Retry policies and circuit breaker settings
- External service integration patterns

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Dict, List, Literal, Optional

from omnibase.enums.enum_node_type import EnumNodeType
from pydantic import BaseModel, Field, validator

from omnibase_core.model.rsd.model_contract_base import ModelContractBase


class ModelIOOperationConfig(BaseModel):
    """
    I/O operation specifications.

    Defines configuration for file operations, database interactions,
    API calls, and other external I/O operations.
    """

    operation_type: str = Field(
        ...,
        description="Type of I/O operation (file_read, file_write, db_query, api_call, etc.)",
        min_length=1,
    )

    atomic: bool = Field(default=True, description="Whether operation should be atomic")

    backup_enabled: bool = Field(
        default=False, description="Enable backup before destructive operations"
    )

    permissions: Optional[str] = Field(
        default=None, description="File permissions or access rights"
    )

    recursive: bool = Field(
        default=False, description="Enable recursive operations for directories"
    )

    buffer_size: int = Field(
        default=8192, description="Buffer size for streaming operations", ge=1024
    )

    timeout_seconds: int = Field(
        default=30, description="Operation timeout in seconds", ge=1
    )

    validation_enabled: bool = Field(
        default=True, description="Enable operation result validation"
    )


class ModelTransactionConfig(BaseModel):
    """
    Transaction management configuration.

    Defines transaction isolation, rollback policies,
    and consistency guarantees for side-effect operations.
    """

    enabled: bool = Field(default=True, description="Enable transaction management")

    isolation_level: str = Field(
        default="read_committed", description="Transaction isolation level"
    )

    timeout_seconds: int = Field(
        default=30, description="Transaction timeout in seconds", ge=1
    )

    rollback_on_error: bool = Field(
        default=True, description="Automatically rollback on error"
    )

    lock_timeout_seconds: int = Field(
        default=10, description="Lock acquisition timeout in seconds", ge=1
    )

    deadlock_retry_count: int = Field(
        default=3, description="Number of retries for deadlock resolution", ge=0
    )

    consistency_check_enabled: bool = Field(
        default=True, description="Enable consistency checking before commit"
    )


class ModelRetryConfig(BaseModel):
    """
    Retry policies and circuit breaker configuration.

    Defines retry strategies, backoff algorithms, and circuit
    breaker patterns for resilient side-effect operations.
    """

    max_attempts: int = Field(default=3, description="Maximum retry attempts", ge=1)

    backoff_strategy: str = Field(
        default="exponential",
        description="Backoff strategy (linear, exponential, constant)",
    )

    base_delay_ms: int = Field(
        default=100, description="Base delay between retries in milliseconds", ge=1
    )

    max_delay_ms: int = Field(
        default=5000, description="Maximum delay between retries in milliseconds", ge=1
    )

    jitter_enabled: bool = Field(
        default=True, description="Enable jitter in retry delays"
    )

    circuit_breaker_enabled: bool = Field(
        default=True, description="Enable circuit breaker pattern"
    )

    circuit_breaker_threshold: int = Field(
        default=5, description="Circuit breaker failure threshold", ge=1
    )

    circuit_breaker_timeout_s: int = Field(
        default=60, description="Circuit breaker timeout in seconds", ge=1
    )

    @validator("max_delay_ms")
    def validate_max_delay_greater_than_base(cls, v, values):
        """Validate max_delay_ms is greater than base_delay_ms."""
        if "base_delay_ms" in values and v <= values["base_delay_ms"]:
            raise ValueError("max_delay_ms must be greater than base_delay_ms")
        return v


class ModelExternalServiceConfig(BaseModel):
    """
    External service integration patterns.

    Defines configuration for external API calls, service
    discovery, authentication, and integration patterns.
    """

    service_type: str = Field(
        ...,
        description="External service type (rest_api, graphql, grpc, message_queue, etc.)",
        min_length=1,
    )

    endpoint_url: Optional[str] = Field(
        default=None, description="Service endpoint URL"
    )

    authentication_method: str = Field(
        default="none",
        description="Authentication method (none, bearer_token, api_key, oauth2)",
    )

    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting for external calls"
    )

    rate_limit_requests_per_minute: int = Field(
        default=60, description="Rate limit: requests per minute", ge=1
    )

    connection_pooling_enabled: bool = Field(
        default=True, description="Enable connection pooling"
    )

    max_connections: int = Field(
        default=10, description="Maximum concurrent connections", ge=1
    )

    timeout_seconds: int = Field(
        default=30, description="Request timeout in seconds", ge=1
    )


class ModelBackupConfig(BaseModel):
    """
    Backup and rollback strategies.

    Defines backup creation, storage, and rollback procedures
    for safe side-effect operations with recovery capabilities.
    """

    enabled: bool = Field(default=True, description="Enable backup creation")

    backup_location: str = Field(
        default="./backups", description="Backup storage location"
    )

    retention_days: int = Field(
        default=7, description="Backup retention period in days", ge=1
    )

    compression_enabled: bool = Field(
        default=True, description="Enable backup compression"
    )

    verification_enabled: bool = Field(
        default=True, description="Enable backup verification after creation"
    )

    rollback_timeout_s: int = Field(
        default=120, description="Maximum rollback operation time in seconds", ge=1
    )


class ModelContractEffect(ModelContractBase):
    """
    Contract model for NodeEffect implementations.

    Specialized contract for side-effect nodes with I/O operations,
    transaction management, and external service integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.EFFECT] = EnumNodeType.EFFECT

    # Side-effect configuration
    io_operations: List[ModelIOOperationConfig] = Field(
        ..., description="I/O operation specifications", min_items=1
    )

    transaction_management: ModelTransactionConfig = Field(
        default_factory=ModelTransactionConfig,
        description="Transaction and rollback configuration",
    )

    retry_policies: ModelRetryConfig = Field(
        default_factory=ModelRetryConfig,
        description="Retry and circuit breaker configuration",
    )

    # External service integration
    external_services: List[ModelExternalServiceConfig] = Field(
        default_factory=list, description="External service integration configurations"
    )

    # Backup and recovery
    backup_config: ModelBackupConfig = Field(
        default_factory=ModelBackupConfig, description="Backup and rollback strategies"
    )

    # Effect-specific settings
    idempotent_operations: bool = Field(
        default=True, description="Whether operations are idempotent"
    )

    side_effect_logging_enabled: bool = Field(
        default=True, description="Enable detailed side-effect operation logging"
    )

    audit_trail_enabled: bool = Field(
        default=True, description="Enable audit trail for all operations"
    )

    consistency_validation_enabled: bool = Field(
        default=True, description="Enable consistency validation after operations"
    )

    def validate_node_specific_config(self) -> None:
        """
        Validate effect node-specific configuration requirements.

        Validates I/O operations, transaction settings, and retry
        policies for effect node compliance.

        Raises:
            ValidationError: If effect-specific validation fails
        """
        # Validate at least one I/O operation is defined
        if not self.io_operations:
            raise ValueError("Effect node must define at least one I/O operation")

        # Validate transaction configuration consistency
        if self.transaction_management.enabled and not any(
            op.atomic for op in self.io_operations
        ):
            raise ValueError(
                "Transaction management requires at least one atomic operation"
            )

        # Validate retry configuration
        if (
            self.retry_policies.circuit_breaker_enabled
            and self.retry_policies.circuit_breaker_threshold
            > self.retry_policies.max_attempts
        ):
            raise ValueError(
                "Circuit breaker threshold cannot exceed max retry attempts"
            )

        # Validate external services have proper configuration
        for service in self.external_services:
            if service.authentication_method != "none" and not service.endpoint_url:
                raise ValueError(
                    "External services with authentication must specify endpoint_url"
                )

    @validator("io_operations")
    def validate_io_operations_consistency(cls, v):
        """Validate I/O operations configuration consistency."""
        operation_types = [op.operation_type for op in v]

        # Check for conflicting atomic requirements
        atomic_ops = [op for op in v if op.atomic]
        non_atomic_ops = [op for op in v if not op.atomic]

        if atomic_ops and non_atomic_ops:
            # This is allowed but should be documented
            pass

        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "forbid"
        use_enum_values = True
        validate_assignment = True
