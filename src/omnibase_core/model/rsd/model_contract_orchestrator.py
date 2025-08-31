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

from typing import Literal

from pydantic import BaseModel, Field, validator

from omnibase_core.enums.node import EnumNodeType
from omnibase_core.model.rsd.model_contract_base import ModelContractBase


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
        description="Event payload field definitions",
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

    filter_conditions: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Event filtering conditions",
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

    trigger_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Event pattern to workflow action mappings",
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


class ModelContractOrchestrator(ModelContractBase):
    """
    Contract model for NodeOrchestrator implementations.

    Specialized contract for workflow coordination nodes with thunk
    emission, conditional branching, and Event Registry integration.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.ORCHESTRATOR] = EnumNodeType.ORCHESTRATOR

    # Orchestration configuration
    thunk_emission: ModelThunkEmissionConfig = Field(
        default_factory=ModelThunkEmissionConfig,
        description="Thunk emission patterns and rules",
    )

    workflow_coordination: ModelWorkflowConfig = Field(
        default_factory=ModelWorkflowConfig,
        description="Workflow coordination and state management",
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

    def validate_node_specific_config(self) -> None:
        """
        Validate orchestrator node-specific configuration requirements.

        Validates thunk emission, workflow coordination, event registry
        integration, and branching logic for orchestrator compliance.

        Raises:
            ValidationError: If orchestrator-specific validation fails
        """
        # Validate thunk emission configuration
        if (
            self.thunk_emission.emission_strategy == "batch"
            and self.thunk_emission.batch_size < 1
        ):
            msg = "Batch emission strategy requires positive batch_size"
            raise ValueError(msg)

        # Validate workflow coordination
        if (
            self.workflow_coordination.execution_mode == "parallel"
            and self.workflow_coordination.max_parallel_branches < 1
        ):
            msg = "Parallel execution requires positive max_parallel_branches"
            raise ValueError(
                msg,
            )

        # Validate checkpoint configuration
        if (
            self.workflow_coordination.checkpoint_enabled
            and self.workflow_coordination.checkpoint_interval_ms < 100
        ):
            msg = "Checkpoint interval must be at least 100ms"
            raise ValueError(msg)

        # Validate branching configuration
        if self.conditional_branching.max_branch_depth < 1:
            msg = "Max branch depth must be at least 1"
            raise ValueError(msg)

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
            raise ValueError(msg)

        # Validate event subscriptions reference valid handlers
        for subscription in self.consumed_events:
            if not subscription.handler_function:
                msg = "Event subscriptions must specify handler_function"
                raise ValueError(msg)

        # Validate performance requirements for orchestrator nodes
        if not self.performance.single_operation_max_ms:
            msg = "Orchestrator nodes must specify single_operation_max_ms performance requirement"
            raise ValueError(
                msg,
            )

    @validator("published_events")
    def validate_published_events_consistency(self, v):
        """Validate published events configuration consistency."""
        # Check for duplicate event names
        event_names = [event.event_name for event in v]
        if len(event_names) != len(set(event_names)):
            msg = "Published events must have unique event names"
            raise ValueError(msg)

        return v

    @validator("consumed_events")
    def validate_consumed_events_consistency(self, v):
        """Validate consumed events configuration consistency."""
        # Check for conflicting batch processing settings
        for subscription in v:
            if subscription.batch_processing and subscription.batch_size < 1:
                msg = "Batch processing requires positive batch_size"
                raise ValueError(msg)

        return v

    @validator("event_coordination")
    def validate_event_coordination_consistency(self, v):
        """Validate event coordination configuration consistency."""
        if v.coordination_strategy == "buffered" and v.buffer_size < 1:
            msg = "Buffered coordination requires positive buffer_size"
            raise ValueError(msg)

        if v.correlation_enabled and v.correlation_timeout_ms < 1000:
            msg = "Event correlation requires timeout of at least 1000ms"
            raise ValueError(msg)

        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "forbid"
        use_enum_values = True
        validate_assignment = True
