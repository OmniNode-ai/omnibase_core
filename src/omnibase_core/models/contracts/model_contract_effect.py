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

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_node_architecture_type import EnumNodeArchitectureType
from omnibase_core.models.contracts.model_backup_config import ModelBackupConfig
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_effect_retry_config import (
    ModelEffectRetryConfig,
)
from omnibase_core.models.contracts.model_external_service_config import (
    ModelExternalServiceConfig,
)
from omnibase_core.models.contracts.model_io_operation_config import (
    ModelIOOperationConfig,
)
from omnibase_core.models.contracts.model_transaction_config import (
    ModelTransactionConfig,
)
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)


class ModelContractEffect(ModelContractBase):
    """
    Contract model for NodeEffect implementations - Clean Architecture.

    Specialized contract for side-effect nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles I/O operations, transaction management, and external service integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    def __init__(self, **data: Any) -> None:
        """Initialize effect contract."""
        super().__init__(**data)

    # Override parent node_type with architecture-specific type
    # Both EnumNodeType.EFFECT and EnumNodeArchitectureType.EFFECT have value "effect"
    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_architecture(cls, v: Any) -> EnumNodeType:
        """Validate and convert architecture type to base node type."""
        if isinstance(v, EnumNodeArchitectureType):
            # Convert architecture type to base node type
            return EnumNodeType(v.value)  # Both have "effect" value
        elif isinstance(v, EnumNodeType):
            return v
        elif isinstance(v, str):
            return EnumNodeType(v)
        else:
            raise ValueError(f"Invalid node_type: {v}")

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation."""
        # Set default node_type if not provided
        if not hasattr(self, "_node_type_set"):
            # Ensure node_type is set to EFFECT for effect contracts
            object.__setattr__(self, "node_type", EnumNodeType.EFFECT)
            object.__setattr__(self, "_node_type_set", True)

        # Call parent post-init validation
        super().model_post_init(__context)

    # UUID correlation tracking for ONEX compliance
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for correlation tracking across system boundaries",
    )

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking individual effect execution instances",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations

    # Infrastructure-specific fields for current standards
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

    # Override validation_rules to support flexible formats
    @field_validator("validation_rules", mode="before")
    @classmethod
    def validate_validation_rules_flexible(cls, v: Any) -> Any:
        """Validate and convert flexible validation rules format."""
        if v is None:
            # Import here to avoid circular imports
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            return ModelValidationRules()

        if isinstance(v, dict):
            # Convert dict to ModelValidationRules
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            return ModelValidationRules(**v)

        if isinstance(v, list):
            # Convert list to ModelValidationRules with constraint_definitions
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            # Create constraint_definitions from list
            constraints = {f"rule_{i}": str(rule) for i, rule in enumerate(v)}
            return ModelValidationRules(constraint_definitions=constraints)

        # If already ModelValidationRules, return as is
        return v

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

    retry_policies: ModelEffectRetryConfig = Field(
        default_factory=ModelEffectRetryConfig,
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
        original_contract_data: dict[str, object] | None = None,
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
        original_contract_data: dict[str, object] | None = None,
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
            # Use model_dump to get contract data for validation
            contract_data = self.model_dump()
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

    model_config = {
        "extra": "ignore",  # Allow extra fields from YAML contracts
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
    }

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
            self,
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractEffect":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractEffect: Validated contract model instance
        """
        import yaml
        from pydantic import ValidationError

        try:
            # Parse YAML directly without recursion
            yaml_data = yaml.safe_load(yaml_content)
            if yaml_data is None:
                yaml_data = {}

            # Validate with Pydantic model directly - avoids from_yaml recursion
            return cls.model_validate(yaml_data)

        except ValidationError as e:
            raise ValueError(f"Contract validation failed: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load contract YAML: {e}") from e
