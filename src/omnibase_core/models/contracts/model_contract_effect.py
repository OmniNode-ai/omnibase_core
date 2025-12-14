"""
Effect Contract Model.



Specialized contract model for NodeEffect implementations providing:
- I/O operation specifications (file, database, API endpoints)
- Transaction management configuration
- Retry policies and circuit breaker settings
- External service integration patterns

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator

from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type aliases for structured data - Strict typing is enforced for Any types
from omnibase_core.types.constraints import PrimitiveValueType

ParameterValue = PrimitiveValueType
StructuredData = dict[str, ParameterValue]
StructuredDataList = list[StructuredData]

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_backup_config import ModelBackupConfig
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_effect_retry_config import (
    ModelEffectRetryConfig,
)
from omnibase_core.models.contracts.model_io_operation_config import (
    ModelIOOperationConfig,
)
from omnibase_core.models.contracts.model_transaction_config import (
    ModelTransactionConfig,
)
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules

# Avoid circular import - import ValidationRulesConverter at function level
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_external_service_config import (
    ModelExternalServiceConfig,
)
from omnibase_core.models.utils.model_subcontract_constraint_validator import (
    ModelSubcontractConstraintValidator,
)

# Import centralized conversion utilities


class ModelContractEffect(MixinNodeTypeValidator, ModelContractBase):
    """
    Contract model for NodeEffect implementations - Clean ModelArchitecture.

    Specialized contract for side-effect nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles I/O operations, transaction management, and external service integration.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Default node type for EFFECT contracts (used by MixinNodeTypeValidator)
    _DEFAULT_NODE_TYPE: ClassVar[EnumNodeType] = EnumNodeType.EFFECT_GENERIC

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation."""
        # Set default node_type if not provided
        if not hasattr(self, "_node_type_set"):
            # Ensure node_type is set to EFFECT_GENERIC for effect contracts
            object.__setattr__(self, "node_type", EnumNodeType.EFFECT_GENERIC)
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

    tool_specification: StructuredData | None = Field(
        default=None,
        description="Tool specification for infrastructure patterns",
    )

    service_configuration: StructuredData | None = Field(
        default=None,
        description="Service configuration for infrastructure patterns",
    )

    input_state: StructuredData | None = Field(
        default=None,
        description="Input state specification",
    )

    output_state: StructuredData | None = Field(
        default=None,
        description="Output state specification",
    )

    actions: StructuredDataList | None = Field(
        default=None,
        description="Action definitions",
    )

    infrastructure: StructuredData | None = Field(
        default=None,
        description="Infrastructure configuration",
    )

    infrastructure_services: StructuredData | None = Field(
        default=None,
        description="Infrastructure services configuration",
    )

    # Override validation_rules to support flexible formats
    @field_validator("validation_rules", mode="before")
    @classmethod
    def validate_validation_rules_flexible(cls, v: object) -> ModelValidationRules:
        """Validate and convert flexible validation rules format using shared utility."""
        # If already a ModelValidationRules instance, return it directly
        # This handles re-validation in pytest-xdist workers where isinstance checks may fail
        # due to module import isolation (each worker has different class objects)
        if isinstance(v, ModelValidationRules):
            return v

        # Local import to avoid circular import
        from omnibase_core.models.utils.model_validation_rules_converter import (
            ModelValidationRulesConverter,
        )

        return ModelValidationRulesConverter.convert_to_validation_rules(v)

    # === CORE EFFECT FUNCTIONALITY ===
    # These fields define the core side-effect behavior

    # Side-effect configuration
    io_operations: list[ModelIOOperationConfig] = Field(
        default=...,
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
        # Validate I/O operations configuration
        self._validate_effect_io_operations()

        # Validate transaction and retry configuration
        self._validate_effect_transaction_config()

        # Validate external services configuration
        self._validate_effect_external_services()

        # Validate infrastructure patterns if present
        self._validate_effect_infrastructure_config()

        # Validate subcontract constraints using shared utility
        ModelSubcontractConstraintValidator.validate_node_subcontract_constraints(
            "effect",
            self.model_dump(),
            original_contract_data,
        )

    def _validate_effect_io_operations(self) -> None:
        """Validate I/O operations configuration for effect nodes."""
        if not self.io_operations:
            msg = "Effect node must define at least one I/O operation"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

    def _validate_effect_transaction_config(self) -> None:
        """Validate transaction management and retry configuration."""
        # Validate transaction configuration consistency
        if self.transaction_management.enabled and not any(
            op.atomic for op in self.io_operations
        ):
            msg = "Transaction management requires at least one atomic operation"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Validate retry configuration
        if (
            self.retry_policies.circuit_breaker_enabled
            and self.retry_policies.circuit_breaker_threshold
            > self.retry_policies.max_attempts
        ):
            msg = "Circuit breaker threshold cannot exceed max retry attempts"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

    def _validate_effect_external_services(self) -> None:
        """Validate external services configuration."""
        # Validate external services have proper configuration
        for service in self.external_services:
            # Check that required services have valid connection config
            if service.required and not service.connection_config:
                msg = f"Required service '{service.service_name}' must have connection_config"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )

    def _validate_effect_infrastructure_config(self) -> None:
        """Validate infrastructure pattern configuration."""
        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise ModelOnexError(
                        message=msg,
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value("valueerror"),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    )

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

    model_config = ConfigDict(
        extra="forbid",  # Strict validation - reject unknown fields
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )

    def to_yaml(self) -> str:
        """
        Export contract model to YAML format.

        Returns:
            str: YAML representation of the contract
        """
        from omnibase_core.utils.util_safe_yaml_loader import (
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
            raise ModelOnexError(
                message=f"Contract validation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"YAML parsing error: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
        except Exception as e:
            raise ModelOnexError(
                message=f"Failed to load contract YAML: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
