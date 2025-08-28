#!/usr/bin/env python3
"""
Orchestrator Contract Model - ONEX Standards Compliant.

Specialized contract model for NodeOrchestrator implementations providing:
- Thunk emission patterns and deferred execution rules
- Conditional branching logic and decision trees
- Parallel execution coordination settings
- Workflow state management and checkpointing
- Event Registry integration for event-driven coordination

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase.core.model_contract_base import ModelContractBase
    from omnibase.enums.enum_node_type import EnumNodeType
else:
    from omnibase.core.model_contract_base import ModelContractBase
    from omnibase.enums.enum_node_type import EnumNodeType

from omnibase.core.subcontracts import (
    ModelEventTypeSubcontract,
    ModelRoutingSubcontract,
    ModelStateManagementSubcontract,
)

from omnibase.core.models.model_semver import ModelSemVer


class ModelDependencySpec(BaseModel):
    """
    Structured dependency specification for orchestrator contracts.

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


class ModelThunkEmissionConfig(BaseModel):
    """
    Thunk emission patterns and deferred execution rules.

    Defines thunk creation, emission timing, and deferred
    execution strategies for workflow coordination.
    """

    emission_strategy: str = Field(
        default="on_demand",
        description="Thunk emission strategy (on_demand, batch, scheduled, event_driven)",
    )

    batch_size: int = Field(
        default=10, description="Batch size for batch emission strategy", ge=1
    )

    max_deferred_thunks: int = Field(
        default=1000, description="Maximum number of deferred thunks", ge=1
    )

    execution_delay_ms: int = Field(
        default=0, description="Delay before thunk execution in milliseconds", ge=0
    )

    priority_based_emission: bool = Field(
        default=True, description="Enable priority-based thunk emission ordering"
    )

    dependency_aware_emission: bool = Field(
        default=True, description="Consider dependencies when emitting thunks"
    )

    retry_failed_thunks: bool = Field(
        default=True, description="Automatically retry failed thunk executions"
    )


class ModelWorkflowDefinition(BaseModel):
    """
    Individual workflow definition with execution patterns.

    Defines a specific workflow with its steps, dependencies,
    and execution configuration.
    """

    workflow_id: str = Field(description="Unique identifier for this workflow")

    workflow_name: str = Field(description="Human-readable name for this workflow")

    workflow_type: str = Field(
        default="sequential",
        description="Workflow type (sequential, parallel, conditional, saga, pipeline)",
    )

    steps: List[Dict[str, Union[str, int, bool]]] = Field(
        default_factory=list,
        description="Ordered list of workflow steps with configuration",
    )

    dependencies: List[str] = Field(
        default_factory=list,
        description="List of workflow IDs this workflow depends on",
    )

    conditions: Optional[Dict[str, Union[str, bool, int]]] = Field(
        default=None, description="Conditions for conditional workflow execution"
    )

    compensation_plan: Optional[Dict[str, Union[str, List[str]]]] = Field(
        default=None, description="Compensation steps for saga pattern workflows"
    )

    priority: int = Field(
        default=100,
        description="Workflow priority (higher numbers = higher priority)",
        ge=1,
        le=1000,
    )


class ModelWorkflowRegistry(BaseModel):
    """
    Registry of available workflows for the orchestrator.

    Maintains multiple workflow definitions that can be
    selected and executed based on request parameters.
    """

    workflows: Dict[str, ModelWorkflowDefinition] = Field(
        default_factory=dict,
        description="Dictionary of workflow_id -> workflow_definition",
    )

    default_workflow_id: str = Field(
        description="Default workflow to use when none specified"
    )

    workflow_selection_strategy: str = Field(
        default="explicit",
        description="Strategy for workflow selection (explicit, conditional, priority_based, load_balanced)",
    )

    max_concurrent_workflows: int = Field(
        default=10, description="Maximum number of concurrent workflow executions", ge=1
    )


class ModelWorkflowConfig(BaseModel):
    """
    Workflow coordination and state management.

    Defines workflow execution patterns, state persistence,
    and coordination strategies for complex workflows.
    """

    execution_mode: str = Field(
        default="sequential",
        description="Workflow execution mode (sequential, parallel, mixed)",
    )

    max_parallel_branches: int = Field(
        default=4, description="Maximum parallel execution branches", ge=1
    )

    checkpoint_enabled: bool = Field(
        default=True, description="Enable workflow checkpointing"
    )

    checkpoint_interval_ms: int = Field(
        default=5000, description="Checkpoint interval in milliseconds", ge=100
    )

    state_persistence_enabled: bool = Field(
        default=True, description="Enable workflow state persistence"
    )

    rollback_enabled: bool = Field(
        default=True, description="Enable workflow rollback capabilities"
    )

    timeout_ms: Optional[int] = Field(
        default=None, description="Workflow execution timeout in milliseconds", ge=1
    )

    recovery_enabled: bool = Field(
        default=True, description="Enable automatic workflow recovery"
    )


class ModelBranchingConfig(BaseModel):
    """
    Conditional branching logic and decision trees.

    Defines conditional logic, decision points, and branching
    strategies for dynamic workflow execution paths.
    """

    decision_points: List[str] = Field(
        default_factory=list, description="Named decision points in the workflow"
    )

    condition_evaluation_strategy: str = Field(
        default="eager",
        description="Condition evaluation strategy (eager, lazy, cached)",
    )

    branch_merge_strategy: str = Field(
        default="wait_all",
        description="Strategy for merging parallel branches (wait_all, wait_any, wait_majority)",
    )

    default_branch_enabled: bool = Field(
        default=True, description="Enable default branch for unmatched conditions"
    )

    condition_timeout_ms: int = Field(
        default=1000,
        description="Timeout for condition evaluation in milliseconds",
        ge=1,
    )

    nested_branching_enabled: bool = Field(
        default=True, description="Enable nested branching structures"
    )

    max_branch_depth: int = Field(
        default=10, description="Maximum branching depth", ge=1
    )


class ModelEventDescriptor(BaseModel):
    """
    Event descriptor models with schema references.

    Defines event structure, schema references, and metadata
    for published events in the Event Registry system.
    """

    event_name: str = Field(
        ..., description="Unique event name identifier", min_length=1
    )

    event_type: str = Field(..., description="Event type classification", min_length=1)

    schema_reference: str = Field(
        ..., description="Reference to event schema definition", min_length=1
    )

    description: str = Field(
        ..., description="Human-readable event description", min_length=1
    )

    version: str = Field(
        default="1.0.0", description="Event schema version", pattern=r"^\d+\.\d+\.\d+$"
    )

    payload_structure: Dict[str, str] = Field(
        default_factory=dict, description="Event payload field definitions"
    )

    metadata_fields: List[str] = Field(
        default_factory=list, description="Required metadata fields"
    )

    criticality_level: str = Field(
        default="normal",
        description="Event criticality level (low, normal, high, critical)",
    )


class ModelEventSubscription(BaseModel):
    """
    Event subscription configuration.

    Defines event consumption patterns, filtering rules,
    and handler configuration for event subscriptions.
    """

    event_pattern: str = Field(
        ..., description="Event name pattern or specific event name", min_length=1
    )

    filter_conditions: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict, description="Event filtering conditions"
    )

    handler_function: str = Field(
        ..., description="Event handler function identifier", min_length=1
    )

    batch_processing: bool = Field(
        default=False, description="Enable batch processing for events"
    )

    batch_size: int = Field(
        default=1, description="Batch size for event processing", ge=1
    )

    timeout_ms: int = Field(
        default=5000, description="Event processing timeout in milliseconds", ge=1
    )

    retry_enabled: bool = Field(
        default=True, description="Enable retry for failed event processing"
    )

    dead_letter_enabled: bool = Field(
        default=True, description="Enable dead letter queue for failed events"
    )


class ModelEventCoordinationConfig(BaseModel):
    """
    Event-driven workflow trigger mappings.

    Defines event-to-workflow mappings, trigger conditions,
    and coordination patterns for event-driven execution.
    """

    trigger_mappings: Dict[str, str] = Field(
        default_factory=dict, description="Event pattern to workflow action mappings"
    )

    coordination_strategy: str = Field(
        default="immediate",
        description="Event coordination strategy (immediate, buffered, scheduled)",
    )

    buffer_size: int = Field(
        default=100, description="Event buffer size for buffered coordination", ge=1
    )

    correlation_enabled: bool = Field(
        default=True, description="Enable event correlation for related events"
    )

    correlation_timeout_ms: int = Field(
        default=10000, description="Correlation timeout in milliseconds", ge=1
    )

    ordering_guaranteed: bool = Field(
        default=False, description="Guarantee event processing order"
    )

    duplicate_detection_enabled: bool = Field(
        default=True, description="Enable duplicate event detection"
    )


class ModelEventRegistryConfig(BaseModel):
    """
    Event Registry integration configuration.

    Defines service discovery, automatic provisioning,
    and registry integration for event management.
    """

    discovery_enabled: bool = Field(
        default=True, description="Enable automatic event discovery"
    )

    auto_provisioning_enabled: bool = Field(
        default=True, description="Enable automatic event provisioning"
    )

    registry_endpoint: Optional[str] = Field(
        default=None, description="Event Registry service endpoint"
    )

    health_check_enabled: bool = Field(
        default=True, description="Enable Event Registry health checking"
    )

    health_check_interval_s: int = Field(
        default=30, description="Health check interval in seconds", ge=1
    )

    cache_enabled: bool = Field(
        default=True, description="Enable registry data caching"
    )

    cache_ttl_s: int = Field(
        default=300, description="Registry cache TTL in seconds", ge=1
    )

    security_enabled: bool = Field(
        default=True, description="Enable security for registry communication"
    )


class ModelContractOrchestrator(ModelContractBase):  # type: ignore[misc]
    """
    Contract model for NodeOrchestrator implementations - Clean Architecture.

    Specialized contract for workflow coordination nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles thunk emission, conditional branching, and Event Registry integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.ORCHESTRATOR] = Field(  # type: ignore[valid-type]
        default=EnumNodeType.ORCHESTRATOR,
        description="Node type classification for 4-node architecture",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations
    
    # Additional orchestrator-specific fields
    node_name: str = Field(
        ..., description="Unique node implementation identifier", min_length=1
    )

    main_tool_class: str = Field(
        ...,
        description="Main implementation class name for instantiation",
        min_length=1,
    )

    # Flexible dependency field supporting multiple formats
    dependencies: Optional[List[Union[str, Dict[str, str], ModelDependencySpec]]] = Field(
        default=None,
        description="Dependencies supporting string, dict, and object formats",
    )
    
    # Infrastructure-specific fields for backward compatibility
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

    # === CORE ORCHESTRATION FUNCTIONALITY ===
    # These fields define the core orchestration behavior

    # Orchestration configuration
    thunk_emission: ModelThunkEmissionConfig = Field(
        default_factory=ModelThunkEmissionConfig,
        description="Thunk emission patterns and rules",
    )

    workflow_coordination: ModelWorkflowConfig = Field(
        default_factory=ModelWorkflowConfig,
        description="Workflow coordination and state management",
    )

    workflow_registry: ModelWorkflowRegistry = Field(
        default_factory=lambda: ModelWorkflowRegistry(default_workflow_id="default"),
        description="Registry of available workflows for selection and execution",
    )

    conditional_branching: ModelBranchingConfig = Field(
        default_factory=ModelBranchingConfig,
        description="Conditional logic and decision trees",
    )

    # Event Registry integration
    event_registry: ModelEventRegistryConfig = Field(
        default_factory=ModelEventRegistryConfig,
        description="Event discovery and provisioning configuration",
    )

    published_events: List[ModelEventDescriptor] = Field(
        default_factory=list, description="Events published by this orchestrator"
    )

    consumed_events: List[ModelEventSubscription] = Field(
        default_factory=list, description="Events consumed by this orchestrator"
    )

    event_coordination: ModelEventCoordinationConfig = Field(
        default_factory=ModelEventCoordinationConfig,
        description="Event-driven workflow trigger mappings",
    )

    # Orchestrator-specific settings
    load_balancing_enabled: bool = Field(
        default=True, description="Enable load balancing across execution nodes"
    )

    failure_isolation_enabled: bool = Field(
        default=True, description="Enable failure isolation between workflow branches"
    )

    monitoring_enabled: bool = Field(
        default=True, description="Enable comprehensive workflow monitoring"
    )

    metrics_collection_enabled: bool = Field(
        default=True, description="Enable metrics collection for workflow execution"
    )

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # Event-driven architecture subcontract
    event_type: Optional[ModelEventTypeSubcontract] = Field(
        default=None,
        description="Event type subcontract for event-driven architecture"
    )

    # Routing subcontract (for workflow and service routing)
    routing: Optional[ModelRoutingSubcontract] = Field(
        default=None,
        description="Routing subcontract for workflow and service routing"
    )

    # State management subcontract (for workflow state)
    state_management: Optional[ModelStateManagementSubcontract] = Field(
        default=None,
        description="State management subcontract for workflow persistence"
    )

    def validate_node_specific_config(self, original_contract_data: Optional[Dict] = None) -> None:
        """
        Validate orchestrator node-specific configuration requirements.

        Contract-driven validation based on what's actually specified in the contract.
        Supports both FSM patterns and infrastructure patterns flexibly.

        Args:
            original_contract_data: The original contract YAML data

        Raises:
            ValidationError: If orchestrator-specific validation fails
        """
        # Validate thunk emission configuration
        if (
            self.thunk_emission.emission_strategy == "batch"
            and self.thunk_emission.batch_size < 1
        ):
            raise ValueError("Batch emission strategy requires positive batch_size")

        # Validate workflow coordination
        if (
            self.workflow_coordination.execution_mode == "parallel"
            and self.workflow_coordination.max_parallel_branches < 1
        ):
            raise ValueError(
                "Parallel execution requires positive max_parallel_branches"
            )

        # Validate checkpoint configuration
        if (
            self.workflow_coordination.checkpoint_enabled
            and self.workflow_coordination.checkpoint_interval_ms < 100
        ):
            raise ValueError("Checkpoint interval must be at least 100ms")

        # Validate branching configuration
        if self.conditional_branching.max_branch_depth < 1:
            raise ValueError("Max branch depth must be at least 1")

        # Validate event registry configuration
        if (
            self.event_registry.discovery_enabled
            and not self.event_registry.registry_endpoint
        ):
            # Auto-discovery is acceptable without explicit endpoint
            pass

        # Validate published events have unique names
        published_names = [event.event_name for event in self.published_events]
        if len(published_names) != len(set(published_names)):
            raise ValueError("Published events must have unique names")

        # Validate event subscriptions reference valid handlers
        for subscription in self.consumed_events:
            if not subscription.handler_function:
                raise ValueError("Event subscriptions must specify handler_function")

        # Validate workflow registry configuration
        if not self.workflow_registry.workflows:
            raise ValueError("Orchestrator must define at least one workflow")

        if (
            self.workflow_registry.default_workflow_id
            not in self.workflow_registry.workflows
        ):
            raise ValueError("Default workflow ID must exist in workflow registry")

        # Validate workflow definitions
        for workflow_id, workflow in self.workflow_registry.workflows.items():
            if not workflow.steps:
                raise ValueError(
                    f"Workflow {workflow_id} must define at least one step"
                )

            # Validate dependencies exist
            for dep_id in workflow.dependencies:
                if dep_id not in self.workflow_registry.workflows:
                    raise ValueError(
                        f"Workflow {workflow_id} depends on non-existent workflow {dep_id}"
                    )

        # Validate performance requirements for orchestrator nodes
        if not self.performance.single_operation_max_ms:
            raise ValueError(
                "Orchestrator nodes must specify single_operation_max_ms performance requirement"
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
        Validate ORCHESTRATOR node subcontract architectural constraints.
        
        ORCHESTRATOR nodes coordinate workflows and can have routing and state_management
        subcontracts, but should not have aggregation subcontracts.
        
        Args:
            original_contract_data: The original contract YAML data
        """
        contract_data = original_contract_data if original_contract_data is not None else self.model_dump()
        violations = []
        
        # ORCHESTRATOR nodes should not have aggregation subcontracts
        if "aggregation" in contract_data:
            violations.append("❌ SUBCONTRACT VIOLATION: ORCHESTRATOR nodes should not have aggregation subcontracts")
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

    @field_validator("published_events")
    @classmethod
    def validate_published_events_consistency(
        cls, v: List[ModelEventDescriptor]
    ) -> List[ModelEventDescriptor]:
        """Validate published events configuration consistency."""
        # Check for duplicate event names
        event_names = [event.event_name for event in v]
        if len(event_names) != len(set(event_names)):
            raise ValueError("Published events must have unique event names")

        return v

    @field_validator("consumed_events")
    @classmethod
    def validate_consumed_events_consistency(
        cls, v: List[ModelEventSubscription]
    ) -> List[ModelEventSubscription]:
        """Validate consumed events configuration consistency."""
        # Check for conflicting batch processing settings
        for subscription in v:
            if subscription.batch_processing and subscription.batch_size < 1:
                raise ValueError("Batch processing requires positive batch_size")

        return v

    @field_validator("event_coordination")
    @classmethod
    def validate_event_coordination_consistency(
        cls, v: ModelEventCoordinationConfig
    ) -> ModelEventCoordinationConfig:
        """Validate event coordination configuration consistency."""
        if v.coordination_strategy == "buffered" and v.buffer_size < 1:
            raise ValueError("Buffered coordination requires positive buffer_size")

        if v.correlation_enabled and v.correlation_timeout_ms < 1000:
            raise ValueError("Event correlation requires timeout of at least 1000ms")

        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
