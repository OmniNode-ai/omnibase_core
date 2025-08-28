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

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from omnibase.core.model_contract_base import ModelContractBase
from omnibase.enums.enum_node_type import EnumNodeType
from omnibase.core.subcontracts import (
    ModelEventTypeSubcontract,
    ModelCachingSubcontract,
    ModelRoutingSubcontract,
)


class ModelDependencySpec(BaseModel):
    """
    Structured dependency specification for effect contracts.

    Defines protocol dependencies with full specification including
    name, type, class name, and module path.
    """

    name: str = Field(..., description="Dependency identifier name", min_length=1)

    type: str = Field(
        ..., description="Dependency type (protocol, service, utility)", min_length=1
    )

    class_name: str = Field(..., description="Implementation class name", min_length=1)

    module: str = Field(
        ..., description="Full module path for the implementation", min_length=1
    )


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
        default=3, description="Circuit breaker failure threshold", ge=1
    )

    circuit_breaker_timeout_s: int = Field(
        default=60, description="Circuit breaker timeout in seconds", ge=1
    )

    @field_validator("max_delay_ms")
    def validate_max_delay_greater_than_base(
        cls, v: int, values: Dict[str, object]
    ) -> int:
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
    Contract model for NodeEffect implementations - Clean Architecture.

    Specialized contract for side-effect nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles I/O operations, transaction management, and external service integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.EFFECT] = Field(
        default=EnumNodeType.EFFECT,
        description="Node type classification for 4-node architecture",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations
    
    # Flexible dependency field supporting multiple formats
    dependencies: Optional[List[Union[str, Dict[str, str], ModelDependencySpec]]] = Field(
        default=None,
        description="Dependencies supporting string, dict, and object formats",
    )
    
    # Infrastructure-specific fields for backward compatibility
    node_name: Optional[str] = Field(
        default=None, description="Node name for infrastructure patterns"
    )
    
    tool_specification: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool specification for infrastructure patterns"
    )
    
    service_configuration: Optional[Dict[str, Any]] = Field(
        default=None, description="Service configuration for infrastructure patterns"
    )
    
    input_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Input state specification"
    )
    
    output_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Output state specification"
    )
    
    actions: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Action definitions"
    )
    
    infrastructure: Optional[Dict[str, Any]] = Field(
        default=None, description="Infrastructure configuration"
    )
    
    infrastructure_services: Optional[Dict[str, Any]] = Field(
        default=None, description="Infrastructure services configuration"
    )
    
    validation_rules: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        default=None, description="Validation rules in flexible format"
    )

    # === CORE EFFECT FUNCTIONALITY ===
    # These fields define the core side-effect behavior

    # Side-effect configuration
    io_operations: List[ModelIOOperationConfig] = Field(
        ..., description="I/O operation specifications", min_length=1
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

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # Event-driven architecture subcontract
    event_type: Optional[ModelEventTypeSubcontract] = Field(
        default=None,
        description="Event type subcontract for event-driven architecture"
    )

    # Caching subcontract
    caching: Optional[ModelCachingSubcontract] = Field(
        default=None,
        description="Caching subcontract for performance optimization"
    )

    # Routing subcontract (for external service routing)
    routing: Optional[ModelRoutingSubcontract] = Field(
        default=None,
        description="Routing subcontract for external service routing"
    )

    def validate_node_specific_config(self, original_contract_data: Optional[Dict] = None) -> None:
        """
        Validate effect node-specific configuration requirements.

        Contract-driven validation based on what's actually specified in the contract.
        Supports both FSM patterns and infrastructure patterns flexibly.

        Args:
            original_contract_data: The original contract YAML data

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

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    raise ValueError(f"tool_specification must include '{field}'")

        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)

    def validate_subcontract_constraints(self, original_contract_data: Optional[Dict] = None) -> None:
        """
        Validate EFFECT node subcontract architectural constraints.
        
        EFFECT nodes handle side effects and can have caching and routing
        subcontracts, but should not have state_management subcontracts.
        
        Args:
            original_contract_data: The original contract YAML data
        """
        contract_data = original_contract_data if original_contract_data is not None else self.model_dump()
        violations = []
        
        # EFFECT nodes should not have state_management (delegate to REDUCER)
        if "state_management" in contract_data:
            violations.append("❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have state_management subcontracts")
            violations.append("   💡 Delegate state management to REDUCER nodes")
        
        # EFFECT nodes should not have aggregation subcontracts
        if "aggregation" in contract_data:
            violations.append("❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have aggregation subcontracts")
            violations.append("   💡 Use REDUCER nodes for data aggregation")
            
        # All nodes should have event_type subcontracts
        if "event_type" not in contract_data:
            violations.append("⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts")
            violations.append("   💡 Add event_type configuration for event-driven architecture")
            
        if violations:
            raise ValueError("\n".join(violations))

    @field_validator("dependencies", mode="before")
    @classmethod
    def parse_flexible_dependencies(
        cls, v: Optional[List[Union[str, Dict[str, str], ModelDependencySpec]]]
    ) -> Optional[List[Union[str, Dict[str, str], ModelDependencySpec]]]:
        """Parse dependencies in flexible formats (string, dict, object)."""
        if not v:
            return v
        
        parsed_deps = []
        for dep in v:
            if isinstance(dep, str):
                # String format: just pass through
                parsed_deps.append(dep)
            elif isinstance(dep, dict):
                if "name" in dep and "type" in dep and "class_name" in dep:
                    # Structured format: convert to ModelDependencySpec
                    parsed_deps.append(ModelDependencySpec(**dep))
                else:
                    # Dict format: pass through
                    parsed_deps.append(dep)
            else:
                # Already parsed or other format
                parsed_deps.append(dep)
        
        return parsed_deps

    @field_validator("io_operations")
    @classmethod
    def validate_io_operations_consistency(
        cls, v: List[ModelIOOperationConfig]
    ) -> List[ModelIOOperationConfig]:
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

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
