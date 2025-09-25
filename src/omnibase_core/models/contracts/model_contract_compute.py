#!/usr/bin/env python3
"""
Compute Contract Model - ONEX Standards Compliant.

Specialized contract model for NodeCompute implementations providing:
- Algorithm specification with factor weights and parameters
- Parallel processing configuration (thread pools, async settings)
- Caching strategies for expensive computations
- Input validation and output transformation rules

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_node_architecture_type import EnumNodeArchitectureType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
    ModelCachingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)

# Import configuration models from individual files
from .model_algorithm_config import ModelAlgorithmConfig
from .model_caching_config import ModelCachingConfig
from .model_input_validation_config import ModelInputValidationConfig
from .model_output_transformation_config import ModelOutputTransformationConfig
from .model_parallel_config import ModelParallelConfig


class ModelContractCompute(ModelContractBase):
    """
    Contract model for NodeCompute implementations - Clean Architecture.

    Specialized contract for pure computation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports algorithm specifications, parallel processing, and caching via subcontracts.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    def __init__(self, **data: Any) -> None:
        """Initialize compute contract."""
        super().__init__(**data)

    # Override parent node_type with architecture-specific type
    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_architecture(cls, v: Any) -> EnumNodeType:
        """Validate and convert architecture type to base node type."""
        if isinstance(v, EnumNodeArchitectureType):
            return EnumNodeType(v.value)  # Both have "compute" value
        elif isinstance(v, EnumNodeType):
            return v
        elif isinstance(v, str):
            return EnumNodeType(v)
        else:
            raise ValueError(f"Invalid node_type: {v}")

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

    # Override validation_rules to support flexible formats
    @field_validator("validation_rules", mode="before")
    @classmethod
    def validate_validation_rules_flexible(cls, v: Any) -> Any:
        """Validate and convert flexible validation rules format."""
        if v is None:
            # Import here to avoid circular imports
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            return ModelValidationRules()

        if isinstance(v, dict):
            # Convert dict to ModelValidationRules
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            return ModelValidationRules(**v)

        if isinstance(v, list):
            # Convert list to ModelValidationRules with constraint_definitions
            from omnibase_core.models.contracts.model_validation_rules import (
                ModelValidationRules,
            )

            # Create constraint_definitions from list
            constraints = {f"rule_{i}": str(rule) for i, rule in enumerate(v)}
            return ModelValidationRules(constraint_definitions=constraints)

        # If already ModelValidationRules, return as is
        return v

    # === CORE COMPUTATION FUNCTIONALITY ===
    # These fields define the core computation behavior

    # Computation configuration
    algorithm: ModelAlgorithmConfig = Field(
        ...,
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
        # Validate algorithm factors are defined
        if not self.algorithm.factors:
            msg = "Compute node must define at least one algorithm factor"
            raise ValueError(msg)

        # Validate parallel processing compatibility
        if (
            self.parallel_processing.enabled
            and self.parallel_processing.max_workers < 1
        ):
            msg = "Parallel processing requires at least 1 worker"
            raise ValueError(msg)

        # Validate caching configuration if present
        if (
            self.caching
            and hasattr(self.caching, "max_entries")
            and self.caching.max_entries < 1
        ):
            msg = "Caching requires positive max_entries"
            raise ValueError(msg)

        # Validate performance requirements for compute nodes
        if not self.performance.single_operation_max_ms:
            msg = "Compute nodes must specify single_operation_max_ms performance requirement"
            raise ValueError(
                msg,
            )

        # Validate tool specification if present (infrastructure pattern)
        if self.tool_specification:
            required_fields = ["tool_name", "main_tool_class"]
            for field in required_fields:
                if field not in self.tool_specification:
                    msg = f"tool_specification must include '{field}'"
                    raise ValueError(msg)

        # Validate subcontract constraints
        self.validate_subcontract_constraints(original_contract_data)

    def validate_subcontract_constraints(
        self,
        original_contract_data: dict[str, object] | None = None,
    ) -> None:
        """
        Validate COMPUTE node subcontract architectural constraints.

        COMPUTE nodes are stateless and should not have state management,
        aggregation, or state transition subcontracts.

        Args:
            original_contract_data: The original contract YAML data
        """
        # Use lazy evaluation for expensive model_dump operation
        if original_contract_data is not None:
            contract_data = original_contract_data
        else:
            # Use model_dump to get contract data for validation
            contract_data = self.model_dump()
        violations = []

        # COMPUTE nodes cannot have state management
        if "state_management" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_management subcontracts",
            )
            violations.append("   💡 Use REDUCER nodes for stateful operations")

        # COMPUTE nodes cannot have aggregation subcontracts
        if "aggregation" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have aggregation subcontracts",
            )
            violations.append("   💡 Use REDUCER nodes for data aggregation")

        # COMPUTE nodes cannot have state transitions
        if "state_transitions" in contract_data:
            violations.append(
                "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_transitions subcontracts",
            )
            violations.append("   💡 Use REDUCER nodes for state machine workflows")

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

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm_consistency(
        cls,
        v: ModelAlgorithmConfig,
    ) -> ModelAlgorithmConfig:
        """Validate algorithm configuration consistency."""
        if v.algorithm_type == "weighted_factor_algorithm" and not v.factors:
            msg = "Weighted factor algorithm requires at least one factor"
            raise ValueError(msg)
        return v

    model_config = {
        "extra": "ignore",  # Allow extra fields from YAML contracts
        "use_enum_values": False,  # Keep enum objects, don't convert to strings
        "validate_assignment": True,
    }

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
            raise ValueError(f"Contract validation failed: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load contract YAML: {e}") from e
