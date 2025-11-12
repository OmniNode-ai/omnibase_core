"""
Compute Contract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
- Breaking changes require major version bump

Specialized contract model for NodeCompute implementations providing:
- Algorithm specification with factor weights and parameters
- Parallel processing configuration (thread pools, async settings)
- Caching strategies for expensive computations
- Input validation and output transformation rules

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_architecture_type import EnumNodeArchitectureType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_lifecycle_config import ModelLifecycleConfig
from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)
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


class ModelContractCompute(ModelContractBase):
    """
    Contract model for NodeCompute implementations - Clean ModelArchitecture.

    Specialized contract for pure computation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports algorithm specifications, parallel processing, and caching via subcontracts.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    def __init__(self, **data: object) -> None:
        """Initialize compute contract."""
        # Extract required parameters from data
        data_dict = dict(data)  # Convert to mutable dict[str, Any]for type safety

        # Required fields with type validation
        name = data_dict.pop("name", None)
        assert isinstance(name, str), f"name must be str, got {type(name)}"

        version = data_dict.pop("version", None)
        assert isinstance(
            version,
            ModelSemVer,
        ), f"version must be ModelSemVer, got {type(version)}"

        description = data_dict.pop("description", None)
        assert isinstance(
            description,
            str,
        ), f"description must be str, got {type(description)}"

        node_type = data_dict.pop("node_type", None)
        assert isinstance(
            node_type,
            EnumNodeType,
        ), f"node_type must be EnumNodeType, got {type(node_type)}"

        input_model = data_dict.pop("input_model", None)
        assert isinstance(
            input_model,
            str,
        ), f"input_model must be str, got {type(input_model)}"

        output_model = data_dict.pop("output_model", None)
        assert isinstance(
            output_model,
            str,
        ), f"output_model must be str, got {type(output_model)}"

        # Optional fields with type validation
        performance = data_dict.pop("performance", None)
        if performance is not None and not isinstance(
            performance,
            ModelPerformanceRequirements,
        ):
            performance = ModelPerformanceRequirements()

        lifecycle = data_dict.pop("lifecycle", None)
        if lifecycle is not None and not isinstance(lifecycle, ModelLifecycleConfig):
            lifecycle = ModelLifecycleConfig()

        dependencies = data_dict.pop("dependencies", None)
        if dependencies is not None and not isinstance(dependencies, list):
            dependencies = []

        protocol_interfaces = data_dict.pop("protocol_interfaces", None)
        if protocol_interfaces is not None and not isinstance(
            protocol_interfaces,
            list,
        ):
            protocol_interfaces = []

        validation_rules = data_dict.pop("validation_rules", None)
        if validation_rules is not None and not isinstance(
            validation_rules,
            ModelValidationRules,
        ):
            validation_rules = None  # Let field validator handle invalid types

        author = data_dict.pop("author", None)
        if author is not None and not isinstance(author, (str, type(None))):
            author = None

        documentation_url = data_dict.pop("documentation_url", None)
        if documentation_url is not None and not isinstance(
            documentation_url,
            (str, type(None)),
        ):
            documentation_url = None

        tags = data_dict.pop("tags", None)
        if tags is not None and not isinstance(tags, list):
            tags = []

        # Call parent constructor with extracted and validated parameters
        super().__init__(
            name=name,
            version=version,
            description=description,
            node_type=node_type,
            input_model=input_model,
            output_model=output_model,
            performance=performance or ModelPerformanceRequirements(),
            lifecycle=lifecycle or ModelLifecycleConfig(),
            dependencies=dependencies or [],
            protocol_interfaces=protocol_interfaces or [],
            validation_rules=validation_rules
            or ModelValidationRules(),  # Use default if None
            author=author,
            documentation_url=documentation_url,
            tags=tags or [],
        )

    # Override parent node_type with architecture-specific type
    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_architecture(cls, v: object) -> EnumNodeType:
        """Validate and convert architecture type to base node type."""
        if isinstance(v, EnumNodeArchitectureType):
            return EnumNodeType(v.value)  # Both have "compute" value
        if isinstance(v, EnumNodeType):
            return v
        if isinstance(v, str):
            try:
                return EnumNodeType(v)
            except ValueError:
                raise ModelOnexError(
                    message=f"Invalid string value for node_type: {v}",
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
        else:
            raise ModelOnexError(
                message=f"Invalid node_type type: {type(v).__name__}",
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

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation."""
        # Set default node_type if not provided
        if not hasattr(self, "_node_type_set"):
            # Ensure node_type is set to COMPUTE for compute contracts
            object.__setattr__(self, "node_type", EnumNodeType.COMPUTE)
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

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm_consistency(
        cls,
        v: ModelAlgorithmConfig,
    ) -> ModelAlgorithmConfig:
        """Validate algorithm configuration consistency."""
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
        extra="ignore",  # Allow extra fields from YAML contracts
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
        except Exception as e:
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
