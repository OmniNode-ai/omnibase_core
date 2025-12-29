"""
Orchestrator Contract Model.

Specialized contract model for NodeOrchestrator implementations providing:
- Thunk emission patterns and deferred execution rules
- Conditional branching logic and decision trees
- Parallel execution coordination settings
- Workflow state management and checkpointing
- Event Registry integration for event-driven coordination

Strict typing is enforced: No Any types allowed in implementation.

Orchestrator Error Hierarchy (v1.0.1 Compliance):
=================================================
This module uses the three-level orchestrator error code hierarchy defined in
EnumCoreErrorCode for consistent, semantically-specific error handling:

Level 1 - Structural Errors (ORCHESTRATOR_STRUCT_*):
    - Detected at contract parse/validation time BEFORE execution
    - Examples: missing required fields, invalid field types, malformed contracts
    - Used for: constraint violations (e.g., batch_size < 1), missing config fields

Level 2 - Semantic Errors (ORCHESTRATOR_SEMANTIC_*):
    - Valid structure but invalid semantics/logic
    - Detected during validation BEFORE workflow execution
    - Examples: duplicate identifiers, circular dependencies, conflicting settings

Level 3 - Execution Errors (ORCHESTRATOR_EXEC_*):
    - Runtime failures during workflow/action execution
    - Detected AFTER validation passes, during actual execution
    - Examples: step timeouts, action rejections, lease expirations

For full documentation, see: docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
"""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
from omnibase_core.models.contracts.model_action_emission_config import (
    ModelActionEmissionConfig,
)
from omnibase_core.models.contracts.model_branching_config import ModelBranchingConfig
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_event_coordination_config import (
    ModelEventCoordinationConfig,
)
from omnibase_core.models.contracts.model_event_registry_config import (
    ModelEventRegistryConfig,
)
from omnibase_core.models.contracts.model_event_subscription import (
    ModelEventSubscription,
)
from omnibase_core.models.contracts.model_workflow_config import ModelWorkflowConfig
from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContractOrchestrator(MixinNodeTypeValidator, ModelContractBase):
    """
    Contract model for NodeOrchestrator implementations.

    Specialized contract for workflow coordination nodes with thunk
    emission, conditional branching, and Event Registry integration.
    Includes UUID correlation tracking for operational traceability.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Default node type for ORCHESTRATOR contracts (used by MixinNodeTypeValidator)
    _DEFAULT_NODE_TYPE: ClassVar[EnumNodeType] = EnumNodeType.ORCHESTRATOR_GENERIC

    # UUID correlation tracking for operational traceability
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking orchestrator operations and debugging",
    )

    node_type: EnumNodeType = Field(
        default=EnumNodeType.ORCHESTRATOR_GENERIC,
        description="Node type classification for 4-node architecture",
    )

    # Orchestration configuration
    action_emission: ModelActionEmissionConfig = Field(
        default_factory=ModelActionEmissionConfig,
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
            ModelOnexError: If orchestrator-specific validation fails
        """
        # Validate thunk emission configuration
        # Structural error: constraint violation on batch_size field
        if (
            self.action_emission.emission_strategy == "batch"
            and self.action_emission.batch_size < 1
        ):
            msg = "Batch emission strategy requires positive batch_size"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        # Validate workflow coordination
        # Structural error: constraint violation on max_parallel_branches field
        if (
            self.workflow_coordination.execution_mode == "parallel"
            and self.workflow_coordination.max_parallel_branches < 1
        ):
            msg = "Parallel execution requires positive max_parallel_branches"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        # Validate checkpoint configuration
        # Structural error: constraint violation on checkpoint_interval_ms field
        if (
            self.workflow_coordination.checkpoint_enabled
            and self.workflow_coordination.checkpoint_interval_ms < 100
        ):
            msg = "Checkpoint interval must be at least 100ms"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        # Validate branching configuration
        # Structural error: constraint violation on max_branch_depth field
        if self.conditional_branching.max_branch_depth < 1:
            msg = "Max branch depth must be at least 1"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        # Validate event registry configuration
        if (
            self.event_registry.discovery_enabled
            and not self.event_registry.registry_endpoint
        ):
            # Auto-discovery is acceptable without explicit endpoint
            pass

        # Validate published events have unique names
        # Semantic error: duplicate identifiers in event names
        published_names = [event.event_name for event in self.published_events]
        if len(published_names) != len(set(published_names)):
            msg = "Published events must have unique names"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID,
            )

        # Validate event subscriptions reference valid handlers
        # Structural error: missing required field handler_function
        for subscription in self.consumed_events:
            if not subscription.handler_function:
                msg = "Event subscriptions must specify handler_function"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MISSING_FIELD,
                )

        # Validate performance requirements for orchestrator nodes
        # Structural error: missing required field single_operation_max_ms
        if not self.performance.single_operation_max_ms:
            msg = "Orchestrator nodes must specify single_operation_max_ms performance requirement"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MISSING_FIELD,
            )

    @field_validator("published_events")
    @classmethod
    def validate_published_events_consistency(
        cls,
        v: list[ModelEventDescriptor],
    ) -> list[ModelEventDescriptor]:
        """
        Validate published events configuration consistency.

        Error codes use the three-level orchestrator hierarchy:
        - Duplicate names: ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID (semantic duplicate)
        """
        # Semantic error: duplicate identifiers in event names
        event_names = [event.event_name for event in v]
        if len(event_names) != len(set(event_names)):
            msg = "Published events must have unique event names"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID,
            )

        return v

    @field_validator("consumed_events")
    @classmethod
    def validate_consumed_events_consistency(
        cls,
        v: list[ModelEventSubscription],
    ) -> list[ModelEventSubscription]:
        """
        Validate consumed events configuration consistency.

        Error codes use the three-level orchestrator hierarchy:
        - Invalid batch_size: ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE (constraint violation)
        """
        # Structural error: constraint violation on batch_size field
        for subscription in v:
            if subscription.batch_processing and subscription.batch_size < 1:
                msg = "Batch processing requires positive batch_size"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
                )

        return v

    @field_validator("event_coordination")
    @classmethod
    def validate_event_coordination_consistency(
        cls,
        v: ModelEventCoordinationConfig,
    ) -> ModelEventCoordinationConfig:
        """
        Validate event coordination configuration consistency.

        Error codes use the three-level orchestrator hierarchy:
        - Invalid buffer_size: ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE (constraint violation)
        - Invalid timeout: ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE (constraint violation)
        """
        # Structural error: constraint violation on buffer_size field
        if v.coordination_strategy == "buffered" and v.buffer_size < 1:
            msg = "Buffered coordination requires positive buffer_size"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        # Structural error: constraint violation on correlation_timeout_ms field
        if v.correlation_enabled and v.correlation_timeout_ms < 1000:
            msg = "Event correlation requires timeout of at least 1000ms"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE,
            )

        return v

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
    )
