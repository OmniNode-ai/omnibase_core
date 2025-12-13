"""
Model for contract content representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed contract content.

"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.configuration.model_metadata_config import ModelMetadataConfig
from omnibase_core.models.contracts.model_algorithm_config import ModelAlgorithmConfig
from omnibase_core.models.contracts.model_caching_config import ModelCachingConfig
from omnibase_core.models.contracts.model_conflict_resolution_config import (
    ModelConflictResolutionConfig,
)
from omnibase_core.models.contracts.model_io_operation_config import (
    ModelIOOperationConfig,
)
from omnibase_core.models.contracts.model_memory_management_config import (
    ModelMemoryManagementConfig,
)
from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_reduction_config import ModelReductionConfig
from omnibase_core.models.contracts.model_streaming_config import ModelStreamingConfig
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules
from omnibase_core.models.contracts.model_workflow_config import ModelWorkflowConfig
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import (
    ModelAggregationSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_observability_subcontract import (
    ModelObservabilitySubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_state_management_subcontract import (
    ModelStateManagementSubcontract,
)
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_contract_dependency import ModelContractDependency
from omnibase_core.models.core.model_state_transition_class import ModelStateTransition
from omnibase_core.models.core.model_subcontract_reference import (
    ModelSubcontractReference,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_service_configuration_single import (
    ModelServiceConfiguration,
)


class ModelContractContent(BaseModel):
    """Model representing contract content structure."""

    model_config = ConfigDict(extra="forbid")

    # === REQUIRED FIELDS ===
    contract_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Contract version",
    )
    node_name: str = Field(default=..., description="Node name")
    node_type: EnumNodeType = Field(
        default=..., description="ONEX node type classification"
    )
    tool_specification: ModelToolSpecification = Field(
        default=...,
        description="Tool specification for NodeBase",
    )
    input_state: ModelYamlSchemaObject = Field(
        default=...,
        description="Input state schema definition",
    )
    output_state: ModelYamlSchemaObject = Field(
        default=...,
        description="Output state schema definition",
    )
    definitions: ModelContractDefinitions = Field(
        default=...,
        description="Contract definitions section",
    )

    # === OPTIONAL COMMON FIELDS ===
    contract_name: str | None = Field(default=None, description="Contract name")
    description: str | None = Field(default=None, description="Contract description")
    name: str | None = Field(default=None, description="Node name alias")
    version: ModelSemVer | None = Field(default=None, description="Version alias")
    node_version: ModelSemVer | None = Field(default=None, description="Node version")
    input_model: str | None = Field(default=None, description="Input model class name")
    output_model: str | None = Field(
        default=None, description="Output model class name"
    )
    main_tool_class: str | None = Field(
        default=None, description="Main tool class name"
    )
    dependencies: list[ModelContractDependency] | None = Field(
        default=None,
        description="Contract dependencies - strongly typed per ONEX Phase 0",
    )
    actions: list[ModelAction] | None = Field(
        default=None,
        description="Available actions - strongly typed orchestrator actions",
    )
    primary_actions: list[str] | None = Field(
        default=None, description="Primary actions"
    )

    @field_validator("validation_rules", mode="before")
    @classmethod
    def validate_validation_rules_flexible(
        cls, v: object
    ) -> ModelValidationRules | None:
        """Validate and convert flexible validation rules format using shared utility."""
        if v is None:
            return None
        if isinstance(v, ModelValidationRules):
            return v
        from omnibase_core.models.utils.model_validation_rules_converter import (
            ModelValidationRulesConverter,
        )

        return ModelValidationRulesConverter.convert_to_validation_rules(v)

    validation_rules: ModelValidationRules | None = Field(
        default=None,
        description="Validation rules for contract enforcement",
    )

    # === INFRASTRUCTURE FIELDS ===
    infrastructure: dict[str, str | int | bool | list[str]] | None = Field(
        default=None,
        description="Infrastructure configuration - basic typed config values",
    )
    infrastructure_services: dict[str, ModelServiceConfiguration] | None = Field(
        default=None,
        description="Infrastructure services - strongly typed service configs",
    )
    service_configuration: ModelServiceConfiguration | None = Field(
        default=None,
        description="Service configuration - strongly typed",
    )
    service_resolution: dict[str, str] | None = Field(
        default=None,
        description="Service resolution mappings - string to string",
    )
    performance: ModelPerformanceRequirements | None = Field(
        default=None,
        description="Performance configuration - strongly typed requirements",
    )

    # === NODE-SPECIFIC FIELDS ===
    # These should only appear in specific node types - architectural validation will catch violations
    aggregation: ModelAggregationSubcontract | None = Field(
        default=None,
        description="Aggregation configuration - COMPUTE nodes should not have this",
    )
    state_management: ModelStateManagementSubcontract | None = Field(
        default=None,
        description="State management configuration - COMPUTE nodes should not have this",
    )
    reduction_operations: list[ModelReductionConfig] | None = Field(
        default=None,
        description="Reduction operations - Only REDUCER nodes",
    )
    streaming: ModelStreamingConfig | None = Field(
        default=None,
        description="Streaming configuration - Only REDUCER nodes",
    )
    conflict_resolution: ModelConflictResolutionConfig | None = Field(
        default=None,
        description="Conflict resolution - Only REDUCER nodes",
    )
    memory_management: ModelMemoryManagementConfig | None = Field(
        default=None,
        description="Memory management - Only REDUCER nodes",
    )
    state_transitions: dict[str, ModelStateTransition] | None = Field(
        default=None,
        description="State transitions - Only REDUCER nodes",
    )
    routing: ModelRoutingSubcontract | None = Field(
        default=None,
        description="Routing configuration - Only ORCHESTRATOR nodes",
    )
    workflow_registry: ModelWorkflowConfig | None = Field(
        default=None,
        description="Workflow registry - Only ORCHESTRATOR nodes",
    )

    # === EFFECT NODE FIELDS ===
    io_operations: list[ModelIOOperationConfig] | None = Field(
        default=None,
        description="I/O operations - Only EFFECT nodes",
    )
    interface: dict[str, str | int | bool | list[str]] | None = Field(
        default=None,
        description="Interface configuration - Only EFFECT nodes (basic typed values)",
    )

    # === OPTIONAL METADATA FIELDS ===
    metadata: ModelMetadataConfig | None = Field(
        default=None, description="Contract metadata - strongly typed"
    )
    capabilities: list[str] | None = Field(
        default=None, description="Node capabilities"
    )
    configuration: dict[str, str | int | bool | float | list[str]] | None = Field(
        default=None,
        description="General configuration - basic typed values",
    )
    algorithm: ModelAlgorithmConfig | None = Field(
        default=None,
        description="Algorithm configuration - strongly typed",
    )
    caching: ModelCachingConfig | None = Field(
        default=None, description="Caching configuration - strongly typed"
    )
    error_handling: dict[str, str | int | bool | list[str]] | None = Field(
        default=None,
        description="Error handling configuration - basic typed values",
    )
    observability: ModelObservabilitySubcontract | None = Field(
        default=None,
        description="Observability configuration - strongly typed subcontract",
    )
    event_type: ModelEventTypeSubcontract | None = Field(
        default=None,
        description="Event type configuration for publish/subscribe patterns - strongly typed",
    )

    # === ONEX COMPLIANCE FLAGS ===
    contract_driven: bool | None = Field(
        default=None,
        description="Contract-driven compliance",
    )
    protocol_based: bool | None = Field(
        default=None,
        description="Protocol-based compliance",
    )
    strong_typing: bool | None = Field(
        default=None, description="Strong typing compliance"
    )
    zero_any_types: bool | None = Field(
        default=None,
        description="Zero Any types compliance",
    )

    # === SUBCONTRACTS ===
    subcontracts: list[ModelSubcontractReference] | None = Field(
        default=None,
        description="Subcontract references for mixin functionality",
    )

    # === DEPRECATED/LEGACY FIELDS ===
    original_dependencies: list[ModelContractDependency] | None = Field(
        default=None,
        description="Original dependencies (deprecated) - use strongly typed dependencies",
    )

    @field_validator("dependencies", mode="before")
    @classmethod
    def convert_dependency_dicts(
        cls, v: object
    ) -> list[ModelContractDependency] | None:
        """Convert dict dependencies to ModelContractDependency instances.

        This prevents Pydantic re-validation issues in parallel execution by
        ensuring all dependencies are properly instantiated before field validation.

        Args:
            v: Dependencies value (list of dicts, ModelContractDependency, or None)

        Returns:
            List of ModelContractDependency instances or None
        """
        if v is None:
            return None
        if not isinstance(v, list):
            return None

        result: list[ModelContractDependency] = []
        for item in v:
            if isinstance(item, dict):
                # Convert dict to ModelContractDependency (triggers its field validators)
                result.append(ModelContractDependency.model_validate(item))
            elif isinstance(item, ModelContractDependency):
                # Already a ModelContractDependency instance
                result.append(item)
        return result
