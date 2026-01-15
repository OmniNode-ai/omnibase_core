"""
Reducer Contract Model (Clean ModelArchitecture) - v1.5.0 Schema.

Specialized contract model for NodeReducer implementations providing:
- Reduction operation specifications with subcontract composition
- Clean separation between node logic and subcontract functionality
- Support for both FSM patterns and simple infrastructure patterns
- Flexible field definitions supporting YAML contract variations
- UUID correlation tracking for traceability
- Contract fingerprint for drift detection (v1.5.0)
- Field aliasing for YAML flexibility (state_machine/state_transitions)
- Thread-safe immutable instances via frozen=True

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type aliases for structured data - Strict typing is enforced for Any types
from omnibase_core.types.type_constraints import PrimitiveValueType

ParameterValue = PrimitiveValueType
StructuredData = dict[str, ParameterValue]
StructuredDataList = list[StructuredData]

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_conflict_resolution_config import (
    ModelConflictResolutionConfig,
)
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_memory_management_config import (
    ModelMemoryManagementConfig,
)
from omnibase_core.models.contracts.model_reduction_config import ModelReductionConfig
from omnibase_core.models.contracts.model_streaming_config import ModelStreamingConfig
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
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContractReducer(MixinNodeTypeValidator, ModelContractBase):
    """
    Contract model for NodeReducer implementations - v1.5.0 Schema.

    Specialized contract for data aggregation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports both FSM complex patterns and simple infrastructure patterns.
    Includes UUID correlation tracking for full traceability.

    Schema Version:
        v1.5.0 - Added fingerprint field for contract drift detection,
        state_machine field with alias support, and frozen model configuration.

    Key Features:
        - fingerprint: Contract identity in format ``<semver>:<sha256_12>`` enabling
          drift detection between YAML contracts and generated code. The semver
          portion tracks schema version, while the 12-character SHA256 hash
          identifies the specific contract content.
        - state_machine: FSM subcontract field with ``alias="state_transitions"``
          allowing YAML contracts to use either field name for flexibility
          with existing contracts.
        - frozen=True: Model instances are immutable after creation, providing
          thread safety for concurrent access and preventing accidental mutation
          of contract state during validation or serialization.

    Note:
        While this model uses ``frozen=True`` for immutability, instances containing
        nested mutable objects (such as lists, dicts, or non-frozen Pydantic models)
        are **not hashable**. This is expected Pydantic behavior: the ``frozen=True``
        configuration prevents field modification but does not make nested mutable
        objects hashable. Attempting to call ``hash()`` on such instances will raise
        ``TypeError: unhashable type``. See tests in
        ``tests/unit/models/contracts/test_model_contract_reducer_v150.py`` for
        detailed documentation of this behavior.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=5, patch=0)

    # Default node type for REDUCER contracts (used by MixinNodeTypeValidator)
    _DEFAULT_NODE_TYPE: ClassVar[EnumNodeType] = EnumNodeType.REDUCER_GENERIC

    # Note: Removed explicit __init__ and model_post_init to avoid MyPy type issues
    # UUID correlation is handled by field default_factory

    # UUID correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for traceability",
    )

    # Contract fingerprint for drift detection (v1.5.0)
    # Format: <semver>:<sha256_12> where semver is the schema version (e.g., 1.5.0)
    # and sha256_12 is the first 12 characters of the SHA256 hash of the contract content.
    # Used to detect when YAML contracts drift from generated code.
    fingerprint: str | None = Field(
        default=None,
        description=(
            "Contract fingerprint for drift detection. Format: <semver>:<sha256_12> "
            "where semver is the schema version (e.g., '1.5.0') and sha256_12 is the "
            "first 12 hex characters of the SHA256 hash of the canonical contract content. "
            "Example: '1.5.0:a1b2c3d4e5f6'. Used to detect contract changes between "
            "YAML definitions and generated code artifacts."
        ),
        pattern=r"^\d+\.\d+\.\d+:[a-f0-9]{12}$",
    )

    node_type: EnumNodeType = Field(
        default=EnumNodeType.REDUCER_GENERIC,
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

    # FSM subcontract for state machine definition (v1.5.0 naming)
    # The alias="state_transitions" supports YAML contracts using the legacy field name.
    # Both field names are accepted when loading from YAML due to populate_by_name=True.
    state_machine: ModelFSMSubcontract | None = Field(
        default=None,
        alias="state_transitions",
        description=(
            "FSM subcontract defining state machine behavior for reducer nodes. "
            "Accepts both 'state_machine' (preferred) and 'state_transitions' (legacy) "
            "field names in YAML contracts via the alias mechanism. The subcontract "
            "defines states, transitions, initial state, and FSM operations with "
            "atomic execution and rollback guarantees for critical operations."
        ),
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
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Validate memory management consistency if present
        if self.memory_management and self.memory_management.spill_to_disk_enabled:
            if self.memory_management.gc_threshold >= 0.9:
                msg = (
                    "GC threshold should be less than 0.9 when spill to disk is enabled"
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )

        # Validate streaming configuration if present
        if self.streaming and self.streaming.enabled and self.streaming.window_size < 1:
            msg = "Streaming requires positive window_size"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise ModelOnexError(
                        message=msg,
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value("valueerror"),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    )

        # Validate FSM subcontract if present
        if self.state_machine is not None:
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

        # REDUCER nodes should have state_machine for proper state management
        # Check both field name and alias for YAML contract validation
        if (
            "state_machine" not in contract_data
            and "state_transitions" not in contract_data
        ):
            violations.append(
                "MISSING SUBCONTRACT: REDUCER nodes should have state_machine subcontracts",
            )
            violations.append(
                "   Add state_machine for proper stateful workflow management",
            )

        # All nodes should have event_type subcontracts
        if "event_type" not in contract_data:
            violations.append(
                "MISSING SUBCONTRACT: All nodes should define event_type subcontracts",
            )
            violations.append(
                "   Add event_type configuration for event-driven architecture",
            )

        if violations:
            raise ModelOnexError(
                message="\n".join(violations),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

    def _validate_fsm_subcontract(self) -> None:
        """
        Validate FSM subcontract configuration for reducer nodes.

        Contract-driven validation - validates what's in the FSM definition.

        Defense-in-Depth Pattern:
            This validation intentionally duplicates some checks that ModelFSMSubcontract
            performs via its @model_validator. This is deliberate:

            1. FSM validators run during FSM construction (ModelFSMSubcontract instantiation)
            2. Contract validators run during contract validation (ModelContractReducer validation)
            3. These are separate validation phases that may execute independently

            By duplicating critical checks here, we:
            - Protect against changes in FSM validation behavior
            - Ensure contract-level invariants hold regardless of FSM implementation details
            - Provide clearer error messages in the contract validation context
            - Enable contracts to enforce stricter requirements than the base FSM model

            This follows the principle: "validate at trust boundaries, not just at the source."
        """
        fsm = self.state_machine
        if fsm is None:
            return

        # Basic structural validation
        if not fsm.initial_state:
            msg = "FSM subcontract must define initial_state"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Validate initial state exists in states list
        state_names = [state.state_name for state in fsm.states]
        if fsm.initial_state not in state_names:
            msg = f"Initial state '{fsm.initial_state}' must be in states list[Any]"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Validate operations have proper atomic guarantees for critical operations
        critical_operations = ["transition", "snapshot", "restore"]
        for operation in fsm.operations:
            if operation.operation_name in critical_operations:
                if not operation.requires_atomic_execution:
                    msg = f"Critical operation '{operation.operation_name}' must require atomic execution"
                    raise ModelOnexError(
                        message=msg,
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value("valueerror"),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    )
                if not operation.supports_rollback:
                    msg = f"Critical operation '{operation.operation_name}' must support rollback"
                    raise ModelOnexError(
                        message=msg,
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value("valueerror"),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    )

    # Pydantic model configuration (v1.5.0)
    # frozen=True ensures thread safety by making instances immutable after creation.
    # This prevents accidental mutation during concurrent access, validation, or
    # serialization operations. Any attempt to modify fields after instantiation
    # will raise a ValidationError.
    # populate_by_name=True enables both field names and aliases to be used when
    # loading from YAML, supporting legacy contracts using state_transitions.
    model_config = ConfigDict(
        extra="forbid",  # Strict validation - reject unknown fields
        from_attributes=True,  # Required for pytest-xdist compatibility
        frozen=True,  # Thread safety and immutability - instances cannot be modified
        populate_by_name=True,  # Allow both field name and alias for YAML flexibility
        str_strip_whitespace=True,  # Clean string inputs
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_default=True,  # Validate default values at model definition time
    )

    def to_yaml(self) -> str:
        """
        Export contract model to YAML format.

        Returns:
            str: YAML representation of the contract
        """
        from omnibase_core.utils.util_safe_yaml_loader import (
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
            raise ModelOnexError(
                message=f"Contract validation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"YAML parsing error: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ) as e:
            # fallback-ok: wraps unexpected parsing errors in ModelOnexError
            raise ModelOnexError(
                message=f"Failed to load contract YAML: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            ) from e
