#!/usr/bin/env python3
"""
Reducer Contract Model - ONEX Standards Compliant (Clean Architecture).

Specialized contract model for NodeReducer implementations providing:
- Reduction operation specifications with subcontract composition
- Clean separation between node logic and subcontract functionality
- Support for both FSM patterns and simple infrastructure patterns
- Flexible field definitions supporting YAML contract variations

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from omnibase.core.model_contract_base import ModelContractBase
from omnibase.enums.enum_node_type import EnumNodeType
from omnibase.core.subcontracts import (
    ModelFSMSubcontract,
    ModelEventTypeSubcontract,
    ModelAggregationSubcontract,
    ModelStateManagementSubcontract,
    ModelCachingSubcontract,
)


class ModelDependencySpec(BaseModel):
    """
    Structured dependency specification for reducer contracts.
    
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


class ModelReductionConfig(BaseModel):
    """
    Data reduction operation specifications.
    
    Defines reduction algorithms, aggregation functions,
    and data processing patterns for efficient data consolidation.
    """
    
    operation_type: str = Field(
        ...,
        description="Type of reduction operation (fold, accumulate, merge, aggregate, etc.)",
        min_length=1,
    )
    
    reduction_function: str = Field(
        ..., description="Reduction function identifier", min_length=1
    )
    
    associative: bool = Field(
        default=True, description="Whether the reduction operation is associative"
    )
    
    commutative: bool = Field(
        default=False, description="Whether the reduction operation is commutative"
    )
    
    identity_element: Optional[str] = Field(
        default=None, description="Identity element for the reduction operation"
    )
    
    chunk_size: int = Field(
        default=1000, description="Chunk size for batch reduction operations", ge=1
    )
    
    parallel_enabled: bool = Field(
        default=True, description="Enable parallel reduction processing"
    )
    
    intermediate_results_caching: bool = Field(
        default=True, description="Cache intermediate reduction results"
    )


class ModelStreamingConfig(BaseModel):
    """
    Streaming configuration for large datasets.
    
    Defines streaming parameters, buffer management,
    and memory-efficient processing for large data volumes.
    """
    
    enabled: bool = Field(default=True, description="Enable streaming processing")
    
    buffer_size: int = Field(
        default=8192, description="Stream buffer size in bytes", ge=1024
    )
    
    window_size: int = Field(
        default=1000,
        description="Processing window size for streaming operations",
        ge=1,
    )
    
    memory_threshold_mb: int = Field(
        default=512, description="Memory threshold for streaming activation in MB", ge=1
    )
    
    backpressure_enabled: bool = Field(
        default=True, description="Enable backpressure handling for streaming"
    )


class ModelConflictResolutionConfig(BaseModel):
    """
    Conflict resolution strategies and merge policies.
    
    Defines conflict detection, resolution strategies,
    and merge policies for handling data conflicts during reduction.
    """
    
    strategy: str = Field(
        default="last_writer_wins",
        description="Conflict resolution strategy (last_writer_wins, first_writer_wins, merge, manual)",
    )
    
    detection_enabled: bool = Field(
        default=True, description="Enable automatic conflict detection"
    )
    
    timestamp_based_resolution: bool = Field(
        default=True, description="Use timestamps for conflict resolution"
    )
    
    conflict_logging_enabled: bool = Field(
        default=True, description="Enable detailed conflict logging"
    )


class ModelMemoryManagementConfig(BaseModel):
    """
    Memory management for batch processing.
    
    Defines memory allocation, garbage collection,
    and resource management for efficient batch processing.
    """
    
    max_memory_mb: int = Field(
        default=1024, description="Maximum memory allocation in MB", ge=1
    )
    
    gc_threshold: float = Field(
        default=0.8,
        description="Garbage collection trigger threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    
    lazy_loading_enabled: bool = Field(
        default=True, description="Enable lazy loading for large datasets"
    )
    
    spill_to_disk_enabled: bool = Field(
        default=True, description="Enable spilling to disk when memory is full"
    )


class ModelContractReducer(ModelContractBase):
    """
    Contract model for NodeReducer implementations - Clean Architecture.
    
    Specialized contract for data aggregation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports both FSM complex patterns and simple infrastructure patterns.
    
    ZERO TOLERANCE: No Any types allowed in implementation.
    """
    
    node_type: Literal[EnumNodeType.REDUCER] = Field(
        default=EnumNodeType.REDUCER,
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
    
    # === CORE REDUCTION FUNCTIONALITY ===
    # These fields define the core reduction behavior
    
    reduction_operations: Optional[List[ModelReductionConfig]] = Field(
        default=None, description="Data reduction operation specifications"
    )
    
    streaming: Optional[ModelStreamingConfig] = Field(
        default=None, description="Streaming configuration"
    )
    
    conflict_resolution: Optional[ModelConflictResolutionConfig] = Field(
        default=None, description="Conflict resolution strategies"
    )
    
    memory_management: Optional[ModelMemoryManagementConfig] = Field(
        default=None, description="Memory management configuration"
    )
    
    # Reducer-specific settings
    order_preserving: bool = Field(
        default=False, description="Whether to preserve input order in reduction"
    )
    
    incremental_processing: bool = Field(
        default=True, description="Enable incremental processing for efficiency"
    )
    
    result_caching_enabled: bool = Field(
        default=True, description="Enable caching of reduction results"
    )
    
    partial_results_enabled: bool = Field(
        default=True, description="Enable returning partial results for long operations"
    )
    
    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration
    
    # FSM subcontract (supports both embedded and $ref patterns)
    state_transitions: Optional[Union[ModelFSMSubcontract, Dict[str, str]]] = Field(
        default=None,
        description="FSM subcontract (embedded definition or $ref reference)",
    )
    
    # Event-driven architecture subcontract
    event_type: Optional[ModelEventTypeSubcontract] = Field(
        default=None,
        description="Event type subcontract for event-driven architecture"
    )
    
    # Aggregation subcontract (reuses aggregation functionality)
    aggregation: Optional[ModelAggregationSubcontract] = Field(
        default=None,
        description="Aggregation subcontract for data processing"
    )
    
    # State management subcontract
    state_management: Optional[ModelStateManagementSubcontract] = Field(
        default=None,
        description="State management subcontract for persistence"
    )
    
    # Caching subcontract
    caching: Optional[ModelCachingSubcontract] = Field(
        default=None,
        description="Caching subcontract for performance optimization"
    )
    
    def validate_node_specific_config(self, original_contract_data: Optional[Dict] = None) -> None:
        """
        Validate reducer node-specific configuration requirements.
        
        Contract-driven validation based on what's actually specified in the contract.
        Supports both FSM patterns and infrastructure patterns flexibly.
        
        Args:
            original_contract_data: The original contract YAML data
            
        Raises:
            ValidationError: If reducer-specific validation fails
        """
        # Validate reduction operations if present
        if self.reduction_operations and self.aggregation:
            if hasattr(self.aggregation, 'aggregation_functions') and not self.aggregation.aggregation_functions:
                raise ValueError(
                    "Reducer with aggregation must define aggregation functions"
                )
        
        # Validate memory management consistency if present
        if self.memory_management and self.memory_management.spill_to_disk_enabled:
            if self.memory_management.gc_threshold >= 0.9:
                raise ValueError("GC threshold should be less than 0.9 when spill to disk is enabled")
        
        # Validate streaming configuration if present
        if self.streaming and self.streaming.enabled and self.streaming.window_size < 1:
            raise ValueError("Streaming requires positive window_size")
        
        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    raise ValueError(f"tool_specification must include '{field}'")
        
        # Validate FSM subcontract if it's not a $ref
        if self.state_transitions and isinstance(self.state_transitions, ModelFSMSubcontract):
            self._validate_fsm_subcontract()
        
        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)
    
    def validate_subcontract_constraints(self, original_contract_data: Optional[Dict] = None) -> None:
        """
        Validate REDUCER node subcontract architectural constraints.
        
        REDUCER nodes are stateful and should have state_transitions subcontracts.
        They can have aggregation and state_management subcontracts.
        
        Args:
            original_contract_data: The original contract YAML data
        """
        contract_data = original_contract_data if original_contract_data is not None else self.model_dump()
        violations = []
        
        # REDUCER nodes should have state_transitions for proper state management
        if "state_transitions" not in contract_data:
            violations.append("⚠️ MISSING SUBCONTRACT: REDUCER nodes should have state_transitions subcontracts")
            violations.append("   💡 Add state_transitions for proper stateful workflow management")
        
        # All nodes should have event_type subcontracts
        if "event_type" not in contract_data:
            violations.append("⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts")
            violations.append("   💡 Add event_type configuration for event-driven architecture")
        
        if violations:
            raise ValueError("\n".join(violations))
    
    def _validate_fsm_subcontract(self) -> None:
        """
        Validate FSM subcontract configuration for reducer nodes.
        
        Contract-driven validation - validates what's in the FSM definition.
        """
        fsm = self.state_transitions
        if not isinstance(fsm, ModelFSMSubcontract):
            return
        
        # Basic structural validation
        if not fsm.initial_state:
            raise ValueError("FSM subcontract must define initial_state")
        
        # Validate initial state exists in states list
        state_names = [state.state_name for state in fsm.states]
        if fsm.initial_state not in state_names:
            raise ValueError(f"Initial state '{fsm.initial_state}' must be in states list")
        
        # Validate operations have proper atomic guarantees for critical operations
        critical_operations = ["transition", "snapshot", "restore"]
        for operation in fsm.operations:
            if operation.operation_name in critical_operations:
                if not operation.requires_atomic_execution:
                    raise ValueError(
                        f"Critical operation '{operation.operation_name}' must require atomic execution"
                    )
                if not operation.supports_rollback:
                    raise ValueError(
                        f"Critical operation '{operation.operation_name}' must support rollback"
                    )
    
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
    
    class Config:
        """Pydantic model configuration for ONEX compliance."""
        
        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True