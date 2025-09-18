"""
Model for contract content representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed contract content.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.node import EnumNodeType
from .model_contract_action import ModelContractAction
from .model_contract_definitions import (
    ModelContractDefinitions,
)
from .model_contract_dependency import ModelContractDependency
from omnibase_core.models.core.model_io_operation import ModelIOOperation
from omnibase_core.models.nodes.model_node_configs import (
    ModelAggregationConfig,
    ModelCachingConfig,
    ModelConflictResolutionConfig,
    ModelErrorHandlingConfig,
    ModelEventTypeConfig,
    ModelInterfaceConfig,
    ModelMemoryManagementConfig,
    ModelObservabilityConfig,
    ModelRoutingConfig,
    ModelStateManagementConfig,
    ModelStreamingConfig,
    ModelWorkflowRegistryConfig,
)
from omnibase_core.models.nodes.model_node_specification import ModelNodeSpecification
from omnibase_core.models.core.model_performance_config import ModelPerformanceConfig
from omnibase_core.models.core.model_reduction_operation import ModelReductionOperation
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.core.model_subcontract_reference import (
    ModelSubcontractReference,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_validation_rule import (
    ModelValidationRule,
    ModelValidationRuleSet,
)
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject

from .model_generic_metadata import ModelGenericMetadata


class ModelContractContent(BaseModel):
    """Model representing contract content structure."""

    model_config = ConfigDict(extra="forbid")

    # === REQUIRED FIELDS ===
    contract_version: ModelSemVer = Field(..., description="Contract version")
    node_name: str = Field(..., description="Node name")
    node_type: EnumNodeType = Field(..., description="ONEX node type classification")
    tool_specification: ModelToolSpecification = Field(
        ...,
        description="Tool specification for NodeBase",
    )
    input_state: ModelYamlSchemaObject = Field(
        ...,
        description="Input state schema definition",
    )
    output_state: ModelYamlSchemaObject = Field(
        ...,
        description="Output state schema definition",
    )
    definitions: ModelContractDefinitions = Field(
        ...,
        description="Contract definitions section",
    )

    # === OPTIONAL COMMON FIELDS ===
    contract_name: str | None = Field(None, description="Contract name")
    description: str | None = Field(None, description="Contract description")
    name: str | None = Field(None, description="Node name alias")
    version: ModelSemVer | None = Field(None, description="Version alias")
    node_version: ModelSemVer | None = Field(None, description="Node version")
    input_model: str | None = Field(None, description="Input model class name")
    output_model: str | None = Field(None, description="Output model class name")
    main_tool_class: str | None = Field(None, description="Main tool class name")
    dependencies: list[ModelContractDependency] | list[str] | None = Field(
        None,
        description="Contract dependencies (can be ModelContractDependency objects or strings)",
    )
    actions: list[ModelContractAction] | None = Field(
        None,
        description="Available actions",
    )
    primary_actions: list[str] | None = Field(None, description="Primary actions")
    validation_rules: ModelValidationRuleSet | list[ModelValidationRule] | None = Field(
        None,
        description="Validation rules (can be rule set or list format)",
    )

    # === INFRASTRUCTURE FIELDS ===
    infrastructure: ModelGenericMetadata | None = Field(
        None,
        description="Infrastructure configuration",
    )
    infrastructure_services: ModelGenericMetadata | None = Field(
        None,
        description="Infrastructure services",
    )
    service_configuration: ModelGenericMetadata | None = Field(
        None,
        description="Service configuration",
    )
    service_resolution: ModelGenericMetadata | None = Field(
        None,
        description="Service resolution",
    )
    performance: ModelPerformanceConfig | None = Field(
        None,
        description="Performance configuration",
    )

    # === NODE-SPECIFIC FIELDS ===
    # These should only appear in specific node types - architectural validation will catch violations
    aggregation: ModelAggregationConfig | None = Field(
        None,
        description="Aggregation configuration - COMPUTE nodes should not have this",
    )
    state_management: ModelStateManagementConfig | None = Field(
        None,
        description="State management configuration - COMPUTE nodes should not have this",
    )
    reduction_operations: list[ModelReductionOperation] | None = Field(
        None,
        description="Reduction operations - Only REDUCER nodes",
    )
    streaming: ModelStreamingConfig | None = Field(
        None,
        description="Streaming configuration - Only REDUCER nodes",
    )
    conflict_resolution: ModelConflictResolutionConfig | None = Field(
        None,
        description="Conflict resolution - Only REDUCER nodes",
    )
    memory_management: ModelMemoryManagementConfig | None = Field(
        None,
        description="Memory management - Only REDUCER nodes",
    )
    state_transitions: ModelStateManagementConfig | None = Field(
        None,
        description="State transitions - Only REDUCER nodes",
    )
    routing: ModelRoutingConfig | None = Field(
        None,
        description="Routing configuration - Only ORCHESTRATOR nodes",
    )
    workflow_registry: ModelWorkflowRegistryConfig | None = Field(
        None,
        description="Workflow registry - Only ORCHESTRATOR nodes",
    )

    # === EFFECT NODE FIELDS ===
    io_operations: list[ModelIOOperation] | None = Field(
        None,
        description="I/O operations - Only EFFECT nodes",
    )
    interface: ModelInterfaceConfig | None = Field(
        None,
        description="Interface configuration - Only EFFECT nodes",
    )

    # === OPTIONAL METADATA FIELDS ===
    metadata: ModelGenericMetadata | None = Field(None, description="Contract metadata")
    capabilities: list[str] | None = Field(None, description="Node capabilities")
    configuration: ModelGenericMetadata | None = Field(
        None,
        description="General configuration",
    )
    algorithm: ModelGenericMetadata | None = Field(
        None,
        description="Algorithm configuration",
    )
    caching: ModelCachingConfig | None = Field(
        None, description="Caching configuration"
    )
    error_handling: ModelErrorHandlingConfig | None = Field(
        None,
        description="Error handling configuration",
    )
    observability: ModelObservabilityConfig | None = Field(
        None,
        description="Observability configuration",
    )
    event_type: ModelEventTypeConfig | None = Field(
        None,
        description="Event type configuration for publish/subscribe patterns",
    )

    # === ONEX COMPLIANCE FLAGS ===
    contract_driven: bool | None = Field(
        None,
        description="Contract-driven compliance",
    )
    protocol_based: bool | None = Field(
        None,
        description="Protocol-based compliance",
    )
    strong_typing: bool | None = Field(None, description="Strong typing compliance")
    zero_any_types: bool | None = Field(
        None,
        description="Zero Any types compliance",
    )

    # === SUBCONTRACTS ===
    subcontracts: list[ModelSubcontractReference] | None = Field(
        None,
        description="Subcontract references for mixin functionality",
    )

    # === DEPRECATED/LEGACY FIELDS ===
    original_dependencies: list[ModelContractDependency] | None = Field(
        None,
        description="Original dependencies (deprecated)",
    )
