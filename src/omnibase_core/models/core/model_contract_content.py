from typing import Dict

from pydantic import Field

from omnibase_core.models.core.model_semver import ModelSemVer

"""
Model for contract content representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed contract content.

Author: ONEX Framework Team
"""

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_contract_dependency import ModelContractDependency
from omnibase_core.models.core.model_subcontract_reference import (
    ModelSubcontractReference,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject


class ModelContractContent(BaseModel):
    """Model representing contract content structure."""

    model_config = ConfigDict(extra="forbid")

    # === REQUIRED FIELDS ===
    contract_version: ModelSemVer = Field(default=..., description="Contract version")
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
    dependencies: list[ModelContractDependency] | list[str] | None = Field(
        default=None,
        description="Contract dependencies (can be ModelContractDependency objects or strings)",
    )
    actions: list[dict[str, Any]] | None = Field(
        default=None,
        description="Available actions",
    )
    primary_actions: list[str] | None = Field(
        default=None, description="Primary actions"
    )
    validation_rules: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Validation rules (can be dict[str, Any]or list[Any]format)",
    )

    # === INFRASTRUCTURE FIELDS ===
    infrastructure: dict[str, Any] | None = Field(
        default=None,
        description="Infrastructure configuration",
    )
    infrastructure_services: dict[str, Any] | None = Field(
        default=None,
        description="Infrastructure services",
    )
    service_configuration: dict[str, Any] | None = Field(
        default=None,
        description="Service configuration",
    )
    service_resolution: dict[str, Any] | None = Field(
        default=None,
        description="Service resolution",
    )
    performance: dict[str, Any] | None = Field(
        default=None,
        description="Performance configuration",
    )

    # === NODE-SPECIFIC FIELDS ===
    # These should only appear in specific node types - architectural validation will catch violations
    aggregation: dict[str, Any] | None = Field(
        default=None,
        description="Aggregation configuration - COMPUTE nodes should not have this",
    )
    state_management: dict[str, Any] | None = Field(
        default=None,
        description="State management configuration - COMPUTE nodes should not have this",
    )
    reduction_operations: list[dict[str, Any]] | None = Field(
        default=None,
        description="Reduction operations - Only REDUCER nodes",
    )
    streaming: dict[str, Any] | None = Field(
        default=None,
        description="Streaming configuration - Only REDUCER nodes",
    )
    conflict_resolution: dict[str, Any] | None = Field(
        default=None,
        description="Conflict resolution - Only REDUCER nodes",
    )
    memory_management: dict[str, Any] | None = Field(
        default=None,
        description="Memory management - Only REDUCER nodes",
    )
    state_transitions: dict[str, Any] | None = Field(
        default=None,
        description="State transitions - Only REDUCER nodes",
    )
    routing: dict[str, Any] | None = Field(
        default=None,
        description="Routing configuration - Only ORCHESTRATOR nodes",
    )
    workflow_registry: dict[str, Any] | None = Field(
        default=None,
        description="Workflow registry - Only ORCHESTRATOR nodes",
    )

    # === EFFECT NODE FIELDS ===
    io_operations: list[dict[str, Any]] | None = Field(
        default=None,
        description="I/O operations - Only EFFECT nodes",
    )
    interface: dict[str, Any] | None = Field(
        default=None,
        description="Interface configuration - Only EFFECT nodes",
    )

    # === OPTIONAL METADATA FIELDS ===
    metadata: dict[str, Any] | None = Field(
        default=None, description="Contract metadata"
    )
    capabilities: list[str] | None = Field(
        default=None, description="Node capabilities"
    )
    configuration: dict[str, Any] | None = Field(
        default=None,
        description="General configuration",
    )
    algorithm: dict[str, Any] | None = Field(
        default=None,
        description="Algorithm configuration",
    )
    caching: dict[str, Any] | None = Field(
        default=None, description="Caching configuration"
    )
    error_handling: dict[str, Any] | None = Field(
        default=None,
        description="Error handling configuration",
    )
    observability: dict[str, Any] | None = Field(
        default=None,
        description="Observability configuration",
    )
    event_type: dict[str, Any] | None = Field(
        default=None,
        description="Event type configuration for publish/subscribe patterns",
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
    original_dependencies: list[dict[str, Any]] | None = Field(
        default=None,
        description="Original dependencies (deprecated)",
    )
