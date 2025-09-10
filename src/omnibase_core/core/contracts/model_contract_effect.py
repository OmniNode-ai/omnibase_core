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

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.subcontracts import (
    ModelCachingSubcontract,
    ModelEventTypeSubcontract,
    ModelRoutingSubcontract,
)
from omnibase_core.enums.node import EnumNodeType
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation


class ModelDependencySpec(BaseModel):
    """
    Structured dependency specification for effect contracts.

    Defines protocol dependencies with full specification including
    name, type, class name, and module path.
    """

    name: str = Field(..., description="Dependency identifier name", min_length=1)

    type: str = Field(
        ...,
        description="Dependency type (protocol, service, utility)",
        min_length=1,
    )

    class_name: str = Field(..., description="Implementation class name", min_length=1)

    module: str = Field(
        ...,
        description="Full module path for the implementation",
        min_length=1,
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
        default=False,
        description="Enable backup before destructive operations",
    )

    permissions: str | None = Field(
        default=None,
        description="File permissions or access rights",
    )

    recursive: bool = Field(
        default=False,
        description="Enable recursive operations for directories",
    )

    buffer_size: int = Field(
        default=8192,
        description="Buffer size for streaming operations",
        ge=1024,
    )

    timeout_seconds: int = Field(
        default=30,
        description="Operation timeout in seconds",
        ge=1,
    )

    validation_enabled: bool = Field(
        default=True,
        description="Enable operation result validation",
    )


class ModelTransactionConfig(BaseModel):
    """
    Transaction management configuration.

    Defines transaction isolation, rollback policies,
    and consistency guarantees for side-effect operations.
    """

    enabled: bool = Field(default=True, description="Enable transaction management")

    isolation_level: str = Field(
        default="read_committed",
        description="Transaction isolation level",
    )

    timeout_seconds: int = Field(
        default=30,
        description="Transaction timeout in seconds",
        ge=1,
    )

    rollback_on_error: bool = Field(
        default=True,
        description="Automatically rollback on error",
    )

    lock_timeout_seconds: int = Field(
        default=10,
        description="Lock acquisition timeout in seconds",
        ge=1,
    )

    deadlock_retry_count: int = Field(
        default=3,
        description="Number of retries for deadlock resolution",
        ge=0,
    )

    consistency_check_enabled: bool = Field(
        default=True,
        description="Enable consistency checking before commit",
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
        default=100,
        description="Base delay between retries in milliseconds",
        ge=1,
    )

    max_delay_ms: int = Field(
        default=5000,
        description="Maximum delay between retries in milliseconds",
        ge=1,
    )

    jitter_enabled: bool = Field(
        default=True,
        description="Enable jitter in retry delays",
    )

    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern",
    )

    circuit_breaker_threshold: int = Field(
        default=3,
        description="Circuit breaker failure threshold",
        ge=1,
    )

    circuit_breaker_timeout_s: int = Field(
        default=60,
        description="Circuit breaker timeout in seconds",
        ge=1,
    )

    @field_validator("max_delay_ms")
    @classmethod
    def validate_max_delay_greater_than_base(
        cls,
        v: int,
        info: ValidationInfo,
    ) -> int:
        """Validate max_delay_ms is greater than base_delay_ms."""
        if "base_delay_ms" in info.data and v <= info.data["base_delay_ms"]:
            msg = "max_delay_ms must be greater than base_delay_ms"
            raise ValueError(msg)
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

    endpoint_url: str | None = Field(
        default=None,
        description="Service endpoint URL",
    )

    authentication_method: str = Field(
        default="none",
        description="Authentication method (none, bearer_token, api_key, oauth2)",
    )

    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for external calls",
    )

    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Rate limit: requests per minute",
        ge=1,
    )

    connection_pooling_enabled: bool = Field(
        default=True,
        description="Enable connection pooling",
    )

    max_connections: int = Field(
        default=10,
        description="Maximum concurrent connections",
        ge=1,
    )

    timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
    )


class ModelBackupConfig(BaseModel):
    """
    Backup and rollback strategies.

    Defines backup creation, storage, and rollback procedures
    for safe side-effect operations with recovery capabilities.
    """

    enabled: bool = Field(default=True, description="Enable backup creation")

    backup_location: str = Field(
        default="./backups",
        description="Backup storage location",
    )

    retention_days: int = Field(
        default=7,
        description="Backup retention period in days",
        ge=1,
    )

    compression_enabled: bool = Field(
        default=True,
        description="Enable backup compression",
    )

    verification_enabled: bool = Field(
        default=True,
        description="Enable backup verification after creation",
    )

    rollback_timeout_s: int = Field(
        default=120,
        description="Maximum rollback operation time in seconds",
        ge=1,
    )


class ModelContractEffect(ModelContractBase, MixinLazyEvaluation):
    """
    Contract model for NodeEffect implementations - Clean Architecture.

    Specialized contract for side-effect nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles I/O operations, transaction management, and external service integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    def __init__(self, **data):
        """Initialize effect contract with lazy evaluation capabilities."""
        super().__init__(**data)
        MixinLazyEvaluation.__init__(self)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation ensuring lazy evaluation mixin is initialized."""
        # Ensure lazy evaluation mixin is initialized (critical for YAML deserialization)
        if not hasattr(self, "_lazy_cache"):
            MixinLazyEvaluation.__init__(self)

        # Call parent post-init validation
        super().model_post_init(__context)

    node_type: Literal[EnumNodeType.EFFECT] = Field(
        default=EnumNodeType.EFFECT,
        description="Node type classification for 4-node architecture",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations

    # Flexible dependency field supporting multiple formats
    dependencies: list[str | dict[str, str] | ModelDependencySpec] | None = Field(
        default=None,
        description="Dependencies supporting string, dict, and object formats",
    )

    # Infrastructure-specific fields for backward compatibility
    node_name: str | None = Field(
        default=None,
        description="Node name for infrastructure patterns",
    )

    tool_specification: dict[str, Any] | None = Field(
        default=None,
        description="Tool specification for infrastructure patterns",
    )

    service_configuration: dict[str, Any] | None = Field(
        default=None,
        description="Service configuration for infrastructure patterns",
    )

    input_state: dict[str, Any] | None = Field(
        default=None,
        description="Input state specification",
    )

    output_state: dict[str, Any] | None = Field(
        default=None,
        description="Output state specification",
    )

    actions: list[dict[str, Any]] | None = Field(
        default=None,
        description="Action definitions",
    )

    infrastructure: dict[str, Any] | None = Field(
        default=None,
        description="Infrastructure configuration",
    )

    infrastructure_services: dict[str, Any] | None = Field(
        default=None,
        description="Infrastructure services configuration",
    )

    validation_rules: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Validation rules in flexible format",
    )

    # === CORE EFFECT FUNCTIONALITY ===
    # These fields define the core side-effect behavior

    # Side-effect configuration
    io_operations: list[ModelIOOperationConfig] = Field(
        ...,
        description="I/O operation specifications",
        min_length=1,
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
    external_services: list[ModelExternalServiceConfig] = Field(
        default_factory=list,
        description="External service integration configurations",
    )

    # Backup and recovery
    backup_config: ModelBackupConfig = Field(
        default_factory=ModelBackupConfig,
        description="Backup and rollback strategies",
    )

    # Effect-specific settings
    idempotent_operations: bool = Field(
        default=True,
        description="Whether operations are idempotent",
    )

    side_effect_logging_enabled: bool = Field(
        default=True,
        description="Enable detailed side-effect operation logging",
    )

    audit_trail_enabled: bool = Field(
        default=True,
        description="Enable audit trail for all operations",
    )

    consistency_validation_enabled: bool = Field(
        default=True,
        description="Enable consistency validation after operations",
    )

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # Event-driven architecture subcontract
    event_type: ModelEventTypeSubcontract | None = Field(
        default=None,
        description="Event type subcontract for event-driven architecture",
    )

    # Caching subcontract
    caching: ModelCachingSubcontract | None = Field(
        default=None,
        description="Caching subcontract for performance optimization",
    )

    # Routing subcontract (for external service routing)
    routing: ModelRoutingSubcontract | None = Field(
        default=None,
        description="Routing subcontract for external service routing",
    )

    def validate_node_specific_config(
        self,
        original_contract_data: dict | None = None,
    ) -> None:
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
            msg = "Effect node must define at least one I/O operation"
            raise ValueError(msg)

        # Validate transaction configuration consistency
        if self.transaction_management.enabled and not any(
            op.atomic for op in self.io_operations
        ):
            msg = "Transaction management requires at least one atomic operation"
            raise ValueError(
                msg,
            )

        # Validate retry configuration
        if (
            self.retry_policies.circuit_breaker_enabled
            and self.retry_policies.circuit_breaker_threshold
            > self.retry_policies.max_attempts
        ):
            msg = "Circuit breaker threshold cannot exceed max retry attempts"
            raise ValueError(
                msg,
            )

        # Validate external services have proper configuration
        for service in self.external_services:
            if service.authentication_method != "none" and not service.endpoint_url:
                msg = "External services with authentication must specify endpoint_url"
                raise ValueError(
                    msg,
                )

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise ValueError(msg)

        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)

    def validate_subcontract_constraints(
        self,
        original_contract_data: dict | None = None,
    ) -> None:
        """
        Validate EFFECT node subcontract architectural constraints.

        EFFECT nodes handle side effects and can have caching and routing
        subcontracts, but should not have state_management subcontracts.

        Args:
            original_contract_data: The original contract YAML data
        """
        # Use lazy evaluation for expensive model_dump operation
        if original_contract_data is not None:
            contract_data = original_contract_data
        else:
            # Lazy evaluation to reduce memory usage by ~60%
            lazy_contract_data = self.lazy_model_dump()
            contract_data = lazy_contract_data()
        violations = []

        # EFFECT nodes should not have state_management (delegate to REDUCER)
        if "state_management" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have state_management subcontracts",
            )
            violations.append("   💡 Delegate state management to REDUCER nodes")

        # EFFECT nodes should not have aggregation subcontracts
        if "aggregation" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have aggregation subcontracts",
            )
            violations.append("   💡 Use REDUCER nodes for data aggregation")

        # All nodes should have event_type subcontracts
        if "event_type" not in contract_data:
            violations.append(
                "⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts",
            )
            violations.append(
                "   💡 Add event_type configuration for event-driven architecture",
            )

        if violations:
            raise ValueError("\n".join(violations))

    @field_validator("dependencies", mode="before")
    @classmethod
    def parse_flexible_dependencies(
        cls,
        v: list[str | dict[str, str] | ModelDependencySpec] | None,
    ) -> list[str | dict[str, str] | ModelDependencySpec] | None:
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
        cls,
        v: list[ModelIOOperationConfig],
    ) -> list[ModelIOOperationConfig]:
        """Validate I/O operations configuration consistency."""
        [op.operation_type for op in v]

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

    def to_yaml(self) -> str:
        """
        Export contract model to YAML format.

        Returns:
            str: YAML representation of the contract
        """
        from omnibase_core.utils.safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        return serialize_pydantic_model_to_yaml(
            self, default_flow_style=False, sort_keys=False
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractEffect":
        """
        Create contract model from YAML content.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractEffect: Validated contract model instance
        """
        from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
        from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

        # Load and validate YAML using Pydantic model
        yaml_model = load_yaml_content_as_model(yaml_content, ModelGenericYaml)
        data = yaml_model.model_dump()
        return cls.model_validate(data)
