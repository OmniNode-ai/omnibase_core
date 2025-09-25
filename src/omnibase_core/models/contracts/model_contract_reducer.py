#!/usr/bin/env python3
"""
Reducer Contract Model - ONEX Standards Compliant (Clean Architecture).

Specialized contract model for NodeReducer implementations providing:
- Reduction operation specifications with subcontract composition
- Clean separation between node logic and subcontract functionality
- Support for both FSM patterns and simple infrastructure patterns
- Flexible field definitions supporting YAML contract variations
- UUID correlation tracking for traceability

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type aliases for structured data - ZERO TOLERANCE for Any types
ParameterValue = Union[str, int, float, bool, None]
StructuredData = dict[str, ParameterValue]
StructuredDataList = list[StructuredData]

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_conflict_resolution_config import (
    ModelConflictResolutionConfig,
)
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_memory_management_config import (
    ModelMemoryManagementConfig,
)
from omnibase_core.models.contracts.model_reduction_config import (
    ModelReductionConfig,
)
from omnibase_core.models.contracts.model_streaming_config import (
    ModelStreamingConfig,
)
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules
from omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract import (
    ModelAggregationSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_state_management_subcontract import (
    ModelStateManagementSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)


class ModelContractReducer(ModelContractBase):
    """
    Contract model for NodeReducer implementations - Clean Architecture.

    Specialized contract for data aggregation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports both FSM complex patterns and simple infrastructure patterns.
    Includes UUID correlation tracking for full traceability.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Note: Removed explicit __init__ and model_post_init to avoid MyPy type issues
    # UUID correlation is handled by field default_factory

    # UUID correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for traceability",
    )

    node_type: EnumNodeType = Field(
        default=EnumNodeType.REDUCER,
        description="Node type classification for 4-node architecture",
    )

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations

    # Infrastructure-specific fields for current standards
    node_name: str | None = Field(
        default=None,
        description="Node name for infrastructure patterns",
    )

    tool_specification: StructuredData | None = Field(
        default=None,
        description="Tool specification for infrastructure patterns",
    )

    service_configuration: StructuredData | None = Field(
        default=None,
        description="Service configuration for infrastructure patterns",
    )

    input_state: StructuredData | None = Field(
        default=None,
        description="Input state specification",
    )

    output_state: StructuredData | None = Field(
        default=None,
        description="Output state specification",
    )

    actions: StructuredDataList | None = Field(
        default=None,
        description="Action definitions",
    )

    infrastructure: StructuredData | None = Field(
        default=None,
        description="Infrastructure configuration",
    )

    infrastructure_services: StructuredData | None = Field(
        default=None,
        description="Infrastructure services configuration",
    )

    validation_rules: ModelValidationRules = Field(
        default_factory=ModelValidationRules,
        description="Validation rules with strong typing",
    )

    # === CORE REDUCTION FUNCTIONALITY ===
    # These fields define the core reduction behavior

    reduction_operations: list[ModelReductionConfig] | None = Field(
        default=None,
        description="Data reduction operation specifications",
    )

    streaming: ModelStreamingConfig | None = Field(
        default=None,
        description="Streaming configuration",
    )

    conflict_resolution: ModelConflictResolutionConfig | None = Field(
        default=None,
        description="Conflict resolution strategies",
    )

    memory_management: ModelMemoryManagementConfig | None = Field(
        default=None,
        description="Memory management configuration",
    )

    # Reducer-specific settings
    order_preserving: bool = Field(
        default=False,
        description="Whether to preserve input order in reduction",
    )

    incremental_processing: bool = Field(
        default=True,
        description="Enable incremental processing for efficiency",
    )

    result_caching_enabled: bool = Field(
        default=True,
        description="Enable caching of reduction results",
    )

    partial_results_enabled: bool = Field(
        default=True,
        description="Enable returning partial results for long operations",
    )

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # FSM subcontract (supports both embedded and $ref patterns)
    state_transitions: ModelFSMSubcontract | dict[str, str] | None = Field(
        default=None,
        description="FSM subcontract (embedded definition or $ref reference)",
    )

    # Event-driven architecture subcontract
    event_type: ModelEventTypeSubcontract | None = Field(
        default=None,
        description="Event type subcontract for event-driven architecture",
    )

    # Aggregation subcontract (reuses aggregation functionality)
    aggregation: ModelAggregationSubcontract | None = Field(
        default=None,
        description="Aggregation subcontract for data processing",
    )

    # State management subcontract
    state_management: ModelStateManagementSubcontract | None = Field(
        default=None,
        description="State management subcontract for persistence",
    )

    # Caching subcontract
    caching: ModelCachingSubcontract | None = Field(
        default=None,
        description="Caching subcontract for performance optimization",
    )

    # Workflow coordination subcontract (CRITICAL for LlamaIndex integration)
    workflow_coordination: ModelWorkflowCoordinationSubcontract | None = Field(
        default=None,
        description="Workflow coordination subcontract for LlamaIndex workflow orchestration",
    )

    def validate_node_specific_config(
        self,
        original_contract_data: StructuredData | None = None,
    ) -> None:
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
        if (
            self.reduction_operations
            and self.aggregation
            and (
                hasattr(self.aggregation, "aggregation_functions")
                and not self.aggregation.aggregation_functions
            )
        ):
            msg = "Reducer with aggregation must define aggregation functions"
            raise ValueError(
                msg,
            )

        # Validate memory management consistency if present
        if self.memory_management and self.memory_management.spill_to_disk_enabled:
            if self.memory_management.gc_threshold >= 0.9:
                msg = (
                    "GC threshold should be less than 0.9 when spill to disk is enabled"
                )
                raise ValueError(
                    msg,
                )

        # Validate streaming configuration if present
        if self.streaming and self.streaming.enabled and self.streaming.window_size < 1:
            msg = "Streaming requires positive window_size"
            raise ValueError(msg)

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise ValueError(msg)

        # Validate FSM subcontract if it's not a $ref
        if self.state_transitions and isinstance(
            self.state_transitions,
            ModelFSMSubcontract,
        ):
            self._validate_fsm_subcontract()

        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)

    def validate_subcontract_constraints(
        self,
        original_contract_data: StructuredData | None = None,
    ) -> None:
        """
        Validate REDUCER node subcontract architectural constraints.

        REDUCER nodes are stateful and should have state_transitions subcontracts.
        They can have aggregation and state_management subcontracts.

        Args:
            original_contract_data: The original contract YAML data
        """
        # Use provided contract data or generate from model
        if original_contract_data is not None:
            contract_data = original_contract_data
        else:
            # Standard model_dump for contract validation
            contract_data = self.model_dump()
        violations = []

        # REDUCER nodes should have state_transitions for proper state management
        if "state_transitions" not in contract_data:
            violations.append(
                "⚠️ MISSING SUBCONTRACT: REDUCER nodes should have state_transitions subcontracts",
            )
            violations.append(
                "   💡 Add state_transitions for proper stateful workflow management",
            )

        # All nodes should have event_type subcontracts
        if "event_type" not in contract_data:
            violations.append(
                "⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts",
            )
            violations.append(
                "   💡 Add event_type configuration for event-driven architecture",
            )

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
            msg = "FSM subcontract must define initial_state"
            raise ValueError(msg)

        # Validate initial state exists in states list
        state_names = [state.state_name for state in fsm.states]
        if fsm.initial_state not in state_names:
            msg = f"Initial state '{fsm.initial_state}' must be in states list"
            raise ValueError(
                msg,
            )

        # Validate operations have proper atomic guarantees for critical operations
        critical_operations = ["transition", "snapshot", "restore"]
        for operation in fsm.operations:
            if operation.operation_name in critical_operations:
                if not operation.requires_atomic_execution:
                    msg = f"Critical operation '{operation.operation_name}' must require atomic execution"
                    raise ValueError(
                        msg,
                    )
                if not operation.supports_rollback:
                    msg = f"Critical operation '{operation.operation_name}' must support rollback"
                    raise ValueError(
                        msg,
                    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

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
    def from_yaml(cls, yaml_content: str) -> "ModelContractReducer":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractReducer: Validated contract model instance
        """
        import yaml
        from pydantic import ValidationError

        try:
            # Parse YAML directly without recursion
            yaml_data = yaml.safe_load(yaml_content)
            if yaml_data is None:
                yaml_data = {}

            # Validate with Pydantic model directly - avoids from_yaml recursion
            return cls.model_validate(yaml_data)

        except ValidationError as e:
            raise ValueError(f"Contract validation failed: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load contract YAML: {e}") from e
