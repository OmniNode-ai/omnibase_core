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

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.contracts.model_branching_config import ModelBranchingConfig
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_event_coordination_config import (
    ModelEventCoordinationConfig,
)
from omnibase_core.models.contracts.model_event_descriptor import ModelEventDescriptor
from omnibase_core.models.contracts.model_event_registry_config import (
    ModelEventRegistryConfig,
)
from omnibase_core.models.contracts.model_event_subscription import (
    ModelEventSubscription,
)
from omnibase_core.models.contracts.model_thunk_emission_config import (
    ModelThunkEmissionConfig,
)
from omnibase_core.models.contracts.model_workflow_config import ModelWorkflowConfig


class ModelContractOrchestrator(ModelContractBase):
    """
    Contract model for NodeOrchestrator implementations.

    Specialized contract for workflow coordination nodes with thunk
    emission, conditional branching, and Event Registry integration.
    Includes UUID correlation tracking for operational traceability.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # UUID correlation tracking for operational traceability
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking orchestrator operations and debugging",
    )

    node_type: EnumNodeType = Field(
        default=EnumNodeType.ORCHESTRATOR,
        description="Node type classification for 4-node architecture",
    )

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
            OnexError: If orchestrator-specific validation fails
        """
        # Validate thunk emission configuration
        if (
            self.thunk_emission.emission_strategy == "batch"
            and self.thunk_emission.batch_size < 1
        ):
            msg = "Batch emission strategy requires positive batch_size"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Validate workflow coordination
        if (
            self.workflow_coordination.execution_mode == "parallel"
            and self.workflow_coordination.max_parallel_branches < 1
        ):
            msg = "Parallel execution requires positive max_parallel_branches"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Validate checkpoint configuration
        if (
            self.workflow_coordination.checkpoint_enabled
            and self.workflow_coordination.checkpoint_interval_ms < 100
        ):
            msg = "Checkpoint interval must be at least 100ms"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Validate branching configuration
        if self.conditional_branching.max_branch_depth < 1:
            msg = "Max branch depth must be at least 1"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
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
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Validate event subscriptions reference valid handlers
        for subscription in self.consumed_events:
            if not subscription.handler_function:
                msg = "Event subscriptions must specify handler_function"
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        # Validate performance requirements for orchestrator nodes
        if not self.performance.single_operation_max_ms:
            msg = "Orchestrator nodes must specify single_operation_max_ms performance requirement"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

    @field_validator("published_events")
    @classmethod
    def validate_published_events_consistency(
        cls, v: list[ModelEventDescriptor]
    ) -> list[ModelEventDescriptor]:
        """Validate published events configuration consistency."""
        # Check for duplicate event names
        event_names = [event.event_name for event in v]
        if len(event_names) != len(set(event_names)):
            msg = "Published events must have unique event names"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("consumed_events")
    @classmethod
    def validate_consumed_events_consistency(
        cls, v: list[ModelEventSubscription]
    ) -> list[ModelEventSubscription]:
        """Validate consumed events configuration consistency."""
        # Check for conflicting batch processing settings
        for subscription in v:
            if subscription.batch_processing and subscription.batch_size < 1:
                msg = "Batch processing requires positive batch_size"
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        return v

    @field_validator("event_coordination")
    @classmethod
    def validate_event_coordination_consistency(
        cls, v: ModelEventCoordinationConfig
    ) -> ModelEventCoordinationConfig:
        """Validate event coordination configuration consistency."""
        if v.coordination_strategy == "buffered" and v.buffer_size < 1:
            msg = "Buffered coordination requires positive buffer_size"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if v.correlation_enabled and v.correlation_timeout_ms < 1000:
            msg = "Event correlation requires timeout of at least 1000ms"
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
    )
