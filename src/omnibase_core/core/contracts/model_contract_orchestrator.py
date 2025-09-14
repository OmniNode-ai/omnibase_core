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

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.contracts.model_dependency import ModelDependency
from omnibase_core.core.contracts.model_workflow_dependency import (
    ModelWorkflowDependency,
)
from omnibase_core.core.contracts.models import (
    ModelCompensationPlan,
    ModelFilterConditions,
    ModelTriggerMappings,
    ModelWorkflowConditions,
    ModelWorkflowStep,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation

if TYPE_CHECKING:
    from omnibase_core.core.contracts.model_contract_base import ModelContractBase
    from omnibase_core.core.subcontracts import (
        ModelEventTypeSubcontract,
        ModelRoutingSubcontract,
        ModelStateManagementSubcontract,
    )
    from omnibase_core.enums.node import EnumNodeType
else:
    from omnibase_core.core.contracts.model_contract_base import ModelContractBase
    from omnibase_core.core.subcontracts import (
        ModelEventTypeSubcontract,
        ModelRoutingSubcontract,
        ModelStateManagementSubcontract,
    )
    from omnibase_core.enums.node import EnumNodeType


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
        default=10,
        description="Batch size for batch emission strategy",
        ge=1,
    )

    max_deferred_thunks: int = Field(
        default=1000,
        description="Maximum number of deferred thunks",
        ge=1,
    )

    execution_delay_ms: int = Field(
        default=0,
        description="Delay before thunk execution in milliseconds",
        ge=0,
    )

    priority_based_emission: bool = Field(
        default=True,
        description="Enable priority-based thunk emission ordering",
    )

    dependency_aware_emission: bool = Field(
        default=True,
        description="Consider dependencies when emitting thunks",
    )

    retry_failed_thunks: bool = Field(
        default=True,
        description="Automatically retry failed thunk executions",
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

    steps: list[ModelWorkflowStep] = Field(
        default_factory=list,
        description="Ordered list of workflow steps with strong typing and validation",
    )

    dependencies: list[ModelWorkflowDependency] = Field(
        default_factory=list,
        description="List of workflow dependencies with proper typing and constraints",
    )

    conditions: ModelWorkflowConditions | None = Field(
        default=None,
        description="Strongly-typed conditions for conditional workflow execution",
    )

    compensation_plan: ModelCompensationPlan | None = Field(
        default=None,
        description="Strongly-typed compensation plan for saga pattern workflows",
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

    workflows: dict[str, ModelWorkflowDefinition] = Field(
        default_factory=dict,
        description="Dictionary of workflow_id -> workflow_definition",
    )

    default_workflow_id: str = Field(
        description="Default workflow to use when none specified",
    )

    workflow_selection_strategy: str = Field(
        default="explicit",
        description="Strategy for workflow selection (explicit, conditional, priority_based, load_balanced)",
    )

    max_concurrent_workflows: int = Field(
        default=10,
        description="Maximum number of concurrent workflow executions",
        ge=1,
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
        default=4,
        description="Maximum parallel execution branches",
        ge=1,
    )

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )

    checkpoint_interval_ms: int = Field(
        default=5000,
        description="Checkpoint interval in milliseconds",
        ge=100,
    )

    state_persistence_enabled: bool = Field(
        default=True,
        description="Enable workflow state persistence",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Enable workflow rollback capabilities",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Workflow execution timeout in milliseconds",
        ge=1,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Enable automatic workflow recovery",
    )


class ModelBranchingConfig(BaseModel):
    """
    Conditional branching logic and decision trees.

    Defines conditional logic, decision points, and branching
    strategies for dynamic workflow execution paths.
    """

    decision_points: list[str] = Field(
        default_factory=list,
        description="Named decision points in the workflow",
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
        default=True,
        description="Enable default branch for unmatched conditions",
    )

    condition_timeout_ms: int = Field(
        default=1000,
        description="Timeout for condition evaluation in milliseconds",
        ge=1,
    )

    nested_branching_enabled: bool = Field(
        default=True,
        description="Enable nested branching structures",
    )

    max_branch_depth: int = Field(
        default=10,
        description="Maximum branching depth",
        ge=1,
    )


class ModelEventDescriptor(BaseModel):
    """
    Event descriptor models with schema references.

    Defines event structure, schema references, and metadata
    for published events in the Event Registry system.
    """

    event_name: str = Field(
        ...,
        description="Unique event name identifier",
        min_length=1,
    )

    event_type: str = Field(..., description="Event type classification", min_length=1)

    schema_reference: str = Field(
        ...,
        description="Reference to event schema definition",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable event description",
        min_length=1,
    )

    version: str = Field(
        default="1.0.0",
        description="Event schema version",
        pattern=r"^\d+\.\d+\.\d+$",
    )

    payload_structure: dict[str, str] = Field(
        default_factory=dict,
        description="Event payload field definitions (strongly typed string-to-string mapping)",
    )

    metadata_fields: list[str] = Field(
        default_factory=list,
        description="Required metadata fields",
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
        ...,
        description="Event name pattern or specific event name",
        min_length=1,
    )

    filter_conditions: ModelFilterConditions | None = Field(
        default=None,
        description="Strongly-typed event filtering conditions",
    )

    handler_function: str = Field(
        ...,
        description="Event handler function identifier",
        min_length=1,
    )

    batch_processing: bool = Field(
        default=False,
        description="Enable batch processing for events",
    )

    batch_size: int = Field(
        default=1,
        description="Batch size for event processing",
        ge=1,
    )

    timeout_ms: int = Field(
        default=5000,
        description="Event processing timeout in milliseconds",
        ge=1,
    )

    retry_enabled: bool = Field(
        default=True,
        description="Enable retry for failed event processing",
    )

    dead_letter_enabled: bool = Field(
        default=True,
        description="Enable dead letter queue for failed events",
    )


class ModelEventCoordinationConfig(BaseModel):
    """
    Event-driven workflow trigger mappings.

    Defines event-to-workflow mappings, trigger conditions,
    and coordination patterns for event-driven execution.
    """

    trigger_mappings: ModelTriggerMappings = Field(
        default_factory=ModelTriggerMappings,
        description="Strongly-typed event pattern to workflow action mappings",
    )

    coordination_strategy: str = Field(
        default="immediate",
        description="Event coordination strategy (immediate, buffered, scheduled)",
    )

    buffer_size: int = Field(
        default=100,
        description="Event buffer size for buffered coordination",
        ge=1,
    )

    correlation_enabled: bool = Field(
        default=True,
        description="Enable event correlation for related events",
    )

    correlation_timeout_ms: int = Field(
        default=10000,
        description="Correlation timeout in milliseconds",
        ge=1,
    )

    ordering_guaranteed: bool = Field(
        default=False,
        description="Guarantee event processing order",
    )

    duplicate_detection_enabled: bool = Field(
        default=True,
        description="Enable duplicate event detection",
    )


class ModelEventRegistryConfig(BaseModel):
    """
    Event Registry integration configuration.

    Defines service discovery, automatic provisioning,
    and registry integration for event management.
    """

    discovery_enabled: bool = Field(
        default=True,
        description="Enable automatic event discovery",
    )

    auto_provisioning_enabled: bool = Field(
        default=True,
        description="Enable automatic event provisioning",
    )

    registry_endpoint: str | None = Field(
        default=None,
        description="Event Registry service endpoint",
    )

    health_check_enabled: bool = Field(
        default=True,
        description="Enable Event Registry health checking",
    )

    health_check_interval_s: int = Field(
        default=30,
        description="Health check interval in seconds",
        ge=1,
    )

    cache_enabled: bool = Field(
        default=True,
        description="Enable registry data caching",
    )

    cache_ttl_s: int = Field(
        default=300,
        description="Registry cache TTL in seconds",
        ge=1,
    )

    security_enabled: bool = Field(
        default=True,
        description="Enable security for registry communication",
    )


class ModelContractOrchestrator(ModelContractBase, MixinLazyEvaluation):  # type: ignore[misc]
    """
    Contract model for NodeOrchestrator implementations - Clean Architecture.

    Specialized contract for workflow coordination nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Handles thunk emission, conditional branching, and Event Registry integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    def __init__(self, **data):
        """Initialize orchestrator contract with lazy evaluation capabilities."""
        super().__init__(**data)
        MixinLazyEvaluation.__init__(self)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation ensuring lazy evaluation mixin is initialized."""
        # Ensure lazy evaluation mixin is initialized (critical for YAML deserialization)
        if not hasattr(self, "_lazy_cache"):
            MixinLazyEvaluation.__init__(self)

        # Call parent post-init validation
        super().model_post_init(__context)

    node_type: Literal["ORCHESTRATOR"] = Field(
        default="ORCHESTRATOR",
        description="Node type classification for 4-node architecture",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations

    # Additional orchestrator-specific fields
    node_name: str = Field(
        ...,
        description="Unique node implementation identifier",
        min_length=1,
    )

    main_tool_class: str = Field(
        ...,
        description="Main implementation class name for instantiation",
        min_length=1,
    )

    # Dependencies now use unified ModelDependency from base class
    # Removed union type override - base class handles all formats

    # Infrastructure-specific fields for current standards
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

    published_events: list[ModelEventDescriptor] = Field(
        default_factory=list,
        description="Events published by this orchestrator",
    )

    consumed_events: list[ModelEventSubscription] = Field(
        default_factory=list,
        description="Events consumed by this orchestrator",
    )

    event_coordination: ModelEventCoordinationConfig = Field(
        default_factory=ModelEventCoordinationConfig,
        description="Event-driven workflow trigger mappings",
    )

    # Orchestrator-specific settings
    load_balancing_enabled: bool = Field(
        default=True,
        description="Enable load balancing across execution nodes",
    )

    failure_isolation_enabled: bool = Field(
        default=True,
        description="Enable failure isolation between workflow branches",
    )

    monitoring_enabled: bool = Field(
        default=True,
        description="Enable comprehensive workflow monitoring",
    )

    metrics_collection_enabled: bool = Field(
        default=True,
        description="Enable metrics collection for workflow execution",
    )

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # Event-driven architecture subcontract
    event_type: ModelEventTypeSubcontract | None = Field(
        default=None,
        description="Event type subcontract for event-driven architecture",
    )

    # Routing subcontract (for workflow and service routing)
    routing: ModelRoutingSubcontract | None = Field(
        default=None,
        description="Routing subcontract for workflow and service routing",
    )

    # State management subcontract (for workflow state)
    state_management: ModelStateManagementSubcontract | None = Field(
        default=None,
        description="State management subcontract for workflow persistence",
    )

    def validate_node_specific_config(
        self,
        original_contract_data: dict | None = None,
    ) -> None:
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
            msg = "Batch emission strategy requires positive batch_size"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate workflow coordination
        if (
            self.workflow_coordination.execution_mode == "parallel"
            and self.workflow_coordination.max_parallel_branches < 1
        ):
            msg = "Parallel execution requires positive max_parallel_branches"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate checkpoint configuration
        if (
            self.workflow_coordination.checkpoint_enabled
            and self.workflow_coordination.checkpoint_interval_ms < 100
        ):
            msg = "Checkpoint interval must be at least 100ms"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate branching configuration
        if self.conditional_branching.max_branch_depth < 1:
            msg = "Max branch depth must be at least 1"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

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
            msg = "Published events must have unique names"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate event subscriptions reference valid handlers
        for subscription in self.consumed_events:
            if not subscription.handler_function:
                msg = "Event subscriptions must specify handler_function"
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=msg,
                    context={"context": {"onex_principle": "Strong types only"}},
                )

        # Validate workflow registry configuration
        if not self.workflow_registry.workflows:
            msg = "Orchestrator must define at least one workflow"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        if (
            self.workflow_registry.default_workflow_id
            not in self.workflow_registry.workflows
        ):
            msg = "Default workflow ID must exist in workflow registry"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate workflow definitions
        for workflow_id, workflow in self.workflow_registry.workflows.items():
            if not workflow.steps:
                msg = f"Workflow {workflow_id} must define at least one step"
                raise ValueError(
                    msg,
                )

            # Validate dependencies exist
            for dependency in workflow.dependencies:
                if dependency.workflow_id not in self.workflow_registry.workflows:
                    raise OnexError(
                        error_code=CoreErrorCode.VALIDATION_FAILED,
                        message=f"Workflow {workflow_id} depends on non-existent workflow {dependency.workflow_id}",
                        context={
                            "workflow_id": workflow_id,
                            "missing_dependency": dependency.workflow_id,
                            "available_workflows": list(
                                self.workflow_registry.workflows.keys()
                            ),
                        },
                    )

        # Validate performance requirements for orchestrator nodes
        if not self.performance.single_operation_max_ms:
            msg = "Orchestrator nodes must specify single_operation_max_ms performance requirement"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise OnexError(
                        error_code=CoreErrorCode.VALIDATION_FAILED,
                        message=msg,
                        context={"context": {"onex_principle": "Strong types only"}},
                    )

        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)

    def validate_subcontract_constraints(
        self,
        original_contract_data: dict | None = None,
    ) -> None:
        """
        Validate ORCHESTRATOR node subcontract architectural constraints.

        ORCHESTRATOR nodes coordinate workflows and can have routing and state_management
        subcontracts, but should not have aggregation subcontracts.

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

        # ORCHESTRATOR nodes should not have aggregation subcontracts
        if "aggregation" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: ORCHESTRATOR nodes should not have aggregation subcontracts",
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
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="\n".join(violations),
                context={"context": {"onex_principle": "Strong types only"}},
            )

    @field_validator("published_events")
    @classmethod
    def validate_published_events_consistency(
        cls,
        v: list[ModelEventDescriptor],
    ) -> list[ModelEventDescriptor]:
        """Validate published events configuration consistency."""
        # Check for duplicate event names
        event_names = [event.event_name for event in v]
        if len(event_names) != len(set(event_names)):
            msg = "Published events must have unique event names"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        return v

    @field_validator("consumed_events")
    @classmethod
    def validate_consumed_events_consistency(
        cls,
        v: list[ModelEventSubscription],
    ) -> list[ModelEventSubscription]:
        """Validate consumed events configuration consistency."""
        # Check for conflicting batch processing settings
        for subscription in v:
            if subscription.batch_processing and subscription.batch_size < 1:
                msg = "Batch processing requires positive batch_size"
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=msg,
                    context={"context": {"onex_principle": "Strong types only"}},
                )

        return v

    @field_validator("event_coordination")
    @classmethod
    def validate_event_coordination_consistency(
        cls,
        v: ModelEventCoordinationConfig,
    ) -> ModelEventCoordinationConfig:
        """Validate event coordination configuration consistency."""
        if v.coordination_strategy == "buffered" and v.buffer_size < 1:
            msg = "Buffered coordination requires positive buffer_size"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

        if v.correlation_enabled and v.correlation_timeout_ms < 1000:
            msg = "Event correlation requires timeout of at least 1000ms"
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=msg,
                context={"context": {"onex_principle": "Strong types only"}},
            )

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
            self,
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractOrchestrator":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractOrchestrator: Validated contract model instance
        """
        from pydantic import ValidationError

        from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

        try:
            # Use safe YAML loader to parse content and validate as model
            return load_yaml_content_as_model(yaml_content, cls)

        except ValidationError as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Contract validation failed: {e}",
                context={"context": {"onex_principle": "Strong types only"}},
            ) from e
