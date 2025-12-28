"""
Compute Contract Model.



Specialized contract model for NodeCompute implementations providing:
- Algorithm specification with factor weights and parameters
- Parallel processing configuration (thread pools, async settings)
- Caching strategies for expensive computations
- Input validation and output transformation rules

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import ConfigDict, Field, field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules

# Avoid circular import - import ValidationRulesConverter at function level
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.utils.model_subcontract_constraint_validator import (
    ModelSubcontractConstraintValidator,
)

# Import configuration models from individual files
from .model_algorithm_config import ModelAlgorithmConfig
from .model_input_validation_config import ModelInputValidationConfig
from .model_output_transformation_config import ModelOutputTransformationConfig
from .model_parallel_config import ModelParallelConfig


class ModelContractCompute(MixinNodeTypeValidator, ModelContractBase):
    """
    Contract model for NodeCompute implementations - Clean ModelArchitecture.

    Specialized contract for pure computation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports algorithm specifications, parallel processing, and caching via subcontracts.

    Strict typing is enforced: No Any types allowed in implementation.

    Required Fields (used by NodeCompute._contract_to_input()):
        **input_state** (for computation input):
            The input_state field is REQUIRED and provides the data for computation.
            An error is raised if input_state is not provided.

        **algorithm.algorithm_type** (for algorithm selection):
            The algorithm_type field in ModelAlgorithmConfig specifies which
            computation to execute. This is a required field.

    Example contract structure::

        algorithm:
          algorithm_type: "my_computation"
          factors:
            factor_1:
              weight: 1.0
        input_state:
          data: "input value"
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Default node type for COMPUTE contracts (used by MixinNodeTypeValidator)
    _DEFAULT_NODE_TYPE: ClassVar[EnumNodeType] = EnumNodeType.COMPUTE_GENERIC

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation."""
        # Set default node_type if not provided
        if not hasattr(self, "_node_type_set"):
            # Ensure node_type is set to COMPUTE_GENERIC for compute contracts
            object.__setattr__(self, "node_type", EnumNodeType.COMPUTE_GENERIC)
            object.__setattr__(self, "_node_type_set", True)

        # Call parent post-init validation
        super().model_post_init(__context)

    # === INFRASTRUCTURE PATTERN SUPPORT ===
    # These fields support infrastructure patterns and YAML variations

    # Flexible dependency field supporting multiple formats
    # Dependencies now use unified ModelDependency from base class
    # Removed union type override - base class handles all formats

    # Infrastructure-specific fields for current standards
    node_name: str | None = Field(
        default=None,
        description="Node name for infrastructure patterns",
    )

    tool_specification: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Tool specification for infrastructure patterns",
    )

    service_configuration: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Service configuration for infrastructure patterns",
    )

    input_state: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Input state specification",
    )

    output_state: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Output state specification",
    )

    actions: list[dict[str, ModelSchemaValue]] | None = Field(
        default=None,
        description="Action definitions",
    )

    infrastructure: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Infrastructure configuration",
    )

    infrastructure_services: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Infrastructure services configuration",
    )

    # Override validation_rules to support flexible formats
    @field_validator("validation_rules", mode="before")
    @classmethod
    def validate_validation_rules_flexible(
        cls,
        v: object,
    ) -> ModelValidationRules:
        """Validate and convert flexible validation rules format using shared utility."""
        # If already a ModelValidationRules instance, return it directly
        # This handles re-validation in pytest-xdist workers where isinstance checks may fail
        # due to module import isolation (each worker has different class objects)
        if isinstance(v, ModelValidationRules):
            return v

        # Local import to avoid circular import
        from omnibase_core.models.utils.model_validation_rules_converter import (
            ModelValidationRulesConverter,
        )

        return ModelValidationRulesConverter.convert_to_validation_rules(v)

    # === CORE COMPUTATION FUNCTIONALITY ===
    # These fields define the core computation behavior

    # Computation configuration
    algorithm: ModelAlgorithmConfig = Field(
        default=...,
        description="Algorithm configuration and parameters",
    )

    parallel_processing: ModelParallelConfig = Field(
        default_factory=ModelParallelConfig,
        description="Parallel execution configuration",
    )

    # Input/Output configuration
    input_validation: ModelInputValidationConfig = Field(
        default_factory=ModelInputValidationConfig,
        description="Input validation and transformation rules",
    )

    output_transformation: ModelOutputTransformationConfig = Field(
        default_factory=ModelOutputTransformationConfig,
        description="Output transformation and formatting rules",
    )

    # Computation-specific settings
    deterministic_execution: bool = Field(
        default=True,
        description="Ensure deterministic execution for same inputs",
    )

    memory_optimization_enabled: bool = Field(
        default=True,
        description="Enable memory optimization strategies",
    )

    intermediate_result_caching: bool = Field(
        default=False,
        description="Enable caching of intermediate computation results",
    )

    # === SUBCONTRACT COMPOSITION ===
    # These fields provide clean subcontract integration

    # Event-driven architecture subcontract
    event_type: ModelEventTypeSubcontract | None = Field(
        default=None,
        description="Event type subcontract for event-driven architecture",
    )

    # Caching subcontract (replaces embedded caching config)
    caching: ModelCachingSubcontract | None = Field(
        default=None,
        description="Caching subcontract for performance optimization",
    )

    def validate_node_specific_config(
        self,
        original_contract_data: dict[str, object] | None = None,
    ) -> None:
        """
        Validate compute node-specific configuration requirements.

        Contract-driven validation based on what's actually specified in the contract.
        Supports both FSM patterns and infrastructure patterns flexibly.

        Args:
            original_contract_data: The original contract YAML data

        Raises:
            ValidationError: If compute-specific validation fails
        """
        # Validate algorithm configuration
        self._validate_compute_algorithm_config()

        # Validate performance and caching configuration
        self._validate_compute_performance_config()

        # Validate infrastructure patterns if present
        self._validate_compute_infrastructure_config()

        # Validate subcontract constraints using shared utility
        ModelSubcontractConstraintValidator.validate_node_subcontract_constraints(
            "compute",
            self.model_dump(),
            original_contract_data,
        )

    def _validate_compute_algorithm_config(self) -> None:
        """Validate algorithm configuration for compute nodes."""
        if not self.algorithm.factors:
            msg = "Compute node must define at least one algorithm factor"
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

    def _validate_compute_performance_config(self) -> None:
        """Validate performance, parallel processing, and caching configuration."""
        # Validate parallel processing compatibility
        if (
            self.parallel_processing.enabled
            and self.parallel_processing.max_workers < 1
        ):
            msg = "Parallel processing requires at least 1 worker"
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

        # Validate caching configuration if present
        if (
            self.caching
            and hasattr(self.caching, "max_entries")
            and self.caching.max_entries < 1
        ):
            msg = "Caching requires positive max_entries"
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

        # Validate performance requirements for compute nodes
        if not self.performance.single_operation_max_ms:
            msg = "Compute nodes must specify single_operation_max_ms performance requirement"
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

    def _validate_compute_infrastructure_config(self) -> None:
        """Validate infrastructure pattern configuration."""
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

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm_from_dict(
        cls,
        v: object,
    ) -> ModelAlgorithmConfig:
        """
        Validate and convert algorithm configuration from dict if needed.

        Supports YAML loading by converting dict to ModelAlgorithmConfig.
        """
        if isinstance(v, ModelAlgorithmConfig):
            return v
        if isinstance(v, dict):
            try:
                return ModelAlgorithmConfig.model_validate(v)
            except (
                AttributeError,
                ValueError,
                TypeError,
                KeyError,
                OSError,
                RuntimeError,
            ) as e:
                raise ModelOnexError(
                    message=f"Invalid algorithm configuration: {e}",
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
        raise ModelOnexError(
            message=f"algorithm must be ModelAlgorithmConfig or dict, got {type(v).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            details=ModelErrorContext.with_context(
                {
                    "error_type": ModelSchemaValue.from_value("typeerror"),
                    "validation_context": ModelSchemaValue.from_value(
                        "model_validation",
                    ),
                },
            ),
        )

    @field_validator("algorithm", mode="after")
    @classmethod
    def validate_algorithm_consistency(
        cls,
        v: ModelAlgorithmConfig,
    ) -> ModelAlgorithmConfig:
        """Validate algorithm configuration consistency after conversion."""
        if v.algorithm_type == "weighted_factor_algorithm" and not v.factors:
            msg = "Weighted factor algorithm requires at least one factor"
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
        return v

    model_config = ConfigDict(
        extra="forbid",  # Strict typing - reject unknown fields
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
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
    def from_yaml(cls, yaml_content: str) -> "ModelContractCompute":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractCompute: Validated contract model instance
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
            ValueError,
            TypeError,
            KeyError,
            OSError,
            RuntimeError,
        ) as e:
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
