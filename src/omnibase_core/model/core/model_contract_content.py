"""
Model for contract content representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed contract content.

Author: ONEX Framework Team
"""

from typing import Any, Dict, List, Optional

from omnibase.enums.enum_node_type import EnumNodeType
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.models.model_contract_definitions import \
    ModelContractDefinitions
from omnibase_core.core.models.model_contract_dependency import \
    ModelContractDependency
from omnibase_core.core.models.model_tool_specification import \
    ModelToolSpecification
from omnibase_core.core.models.model_yaml_schema_object import \
    ModelYamlSchemaObject
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelContractContent(BaseModel):
    """Model representing contract content structure."""

    model_config = ConfigDict(extra="forbid")

    # === REQUIRED FIELDS ===
    contract_version: ModelSemVer = Field(..., description="Contract version")
    node_name: str = Field(..., description="Node name")
    node_type: EnumNodeType = Field(..., description="ONEX node type classification")
    tool_specification: ModelToolSpecification = Field(
        ..., description="Tool specification for NodeBase"
    )
    input_state: ModelYamlSchemaObject = Field(
        ..., description="Input state schema definition"
    )
    output_state: ModelYamlSchemaObject = Field(
        ..., description="Output state schema definition"
    )
    definitions: ModelContractDefinitions = Field(
        ..., description="Contract definitions section"
    )

    # === OPTIONAL COMMON FIELDS ===
    contract_name: Optional[str] = Field(None, description="Contract name")
    description: Optional[str] = Field(None, description="Contract description")
    name: Optional[str] = Field(None, description="Node name alias")
    version: Optional[ModelSemVer] = Field(None, description="Version alias")
    node_version: Optional[ModelSemVer] = Field(None, description="Node version")
    input_model: Optional[str] = Field(None, description="Input model class name")
    output_model: Optional[str] = Field(None, description="Output model class name")
    main_tool_class: Optional[str] = Field(None, description="Main tool class name")
    dependencies: Optional[List[ModelContractDependency]] = Field(
        None, description="Contract dependencies for Phase 0 pattern"
    )
    actions: Optional[List[Dict[str, Any]]] = Field(
        None, description="Available actions"
    )
    primary_actions: Optional[List[str]] = Field(None, description="Primary actions")
    validation_rules: Optional[List[Dict[str, Any]]] = Field(
        None, description="Validation rules"
    )

    # === INFRASTRUCTURE FIELDS ===
    infrastructure: Optional[Dict[str, Any]] = Field(
        None, description="Infrastructure configuration"
    )
    infrastructure_services: Optional[Dict[str, Any]] = Field(
        None, description="Infrastructure services"
    )
    service_configuration: Optional[Dict[str, Any]] = Field(
        None, description="Service configuration"
    )
    service_resolution: Optional[Dict[str, Any]] = Field(
        None, description="Service resolution"
    )
    performance: Optional[Dict[str, Any]] = Field(
        None, description="Performance configuration"
    )

    # === NODE-SPECIFIC FIELDS ===
    # These should only appear in specific node types - architectural validation will catch violations
    aggregation: Optional[Dict[str, Any]] = Field(
        None,
        description="Aggregation configuration - COMPUTE nodes should not have this",
    )
    state_management: Optional[Dict[str, Any]] = Field(
        None,
        description="State management configuration - COMPUTE nodes should not have this",
    )
    reduction_operations: Optional[List[Dict[str, Any]]] = Field(
        None, description="Reduction operations - Only REDUCER nodes"
    )
    streaming: Optional[Dict[str, Any]] = Field(
        None, description="Streaming configuration - Only REDUCER nodes"
    )
    conflict_resolution: Optional[Dict[str, Any]] = Field(
        None, description="Conflict resolution - Only REDUCER nodes"
    )
    memory_management: Optional[Dict[str, Any]] = Field(
        None, description="Memory management - Only REDUCER nodes"
    )
    state_transitions: Optional[Dict[str, Any]] = Field(
        None, description="State transitions - Only REDUCER nodes"
    )
    routing: Optional[Dict[str, Any]] = Field(
        None, description="Routing configuration - Only ORCHESTRATOR nodes"
    )
    workflow_registry: Optional[Dict[str, Any]] = Field(
        None, description="Workflow registry - Only ORCHESTRATOR nodes"
    )

    # === EFFECT NODE FIELDS ===
    io_operations: Optional[List[Dict[str, Any]]] = Field(
        None, description="I/O operations - Only EFFECT nodes"
    )
    interface: Optional[Dict[str, Any]] = Field(
        None, description="Interface configuration - Only EFFECT nodes"
    )

    # === OPTIONAL METADATA FIELDS ===
    metadata: Optional[Dict[str, Any]] = Field(None, description="Contract metadata")
    capabilities: Optional[List[str]] = Field(None, description="Node capabilities")
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="General configuration"
    )
    algorithm: Optional[Dict[str, Any]] = Field(
        None, description="Algorithm configuration"
    )
    caching: Optional[Dict[str, Any]] = Field(None, description="Caching configuration")
    error_handling: Optional[Dict[str, Any]] = Field(
        None, description="Error handling configuration"
    )
    observability: Optional[Dict[str, Any]] = Field(
        None, description="Observability configuration"
    )

    # === ONEX COMPLIANCE FLAGS ===
    contract_driven: Optional[bool] = Field(
        None, description="Contract-driven compliance"
    )
    protocol_based: Optional[bool] = Field(
        None, description="Protocol-based compliance"
    )
    strong_typing: Optional[bool] = Field(None, description="Strong typing compliance")
    zero_any_types: Optional[bool] = Field(
        None, description="Zero Any types compliance"
    )

    # === DEPRECATED/LEGACY FIELDS ===
    original_dependencies: Optional[List[Dict[str, Any]]] = Field(
        None, description="Original dependencies (deprecated)"
    )
