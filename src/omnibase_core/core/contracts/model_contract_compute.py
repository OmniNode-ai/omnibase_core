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

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.subcontracts import (
    ModelCachingSubcontract,
    ModelEventTypeSubcontract,
)
from omnibase_core.enums import EnumNodeType
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation


class ModelAlgorithmFactorConfig(BaseModel):
    """
    Configuration for individual algorithm factors.

    Defines weight, calculation method, and parameters for
    each factor in a multi-factor algorithm.
    """

    weight: float = Field(
        ...,
        description="Factor weight in algorithm (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    calculation_method: str = Field(
        ...,
        description="Calculation method identifier",
        min_length=1,
    )

    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Method-specific parameters",
    )

    normalization_enabled: bool = Field(
        default=True,
        description="Enable factor normalization",
    )

    caching_enabled: bool = Field(
        default=True,
        description="Enable factor-level caching",
    )


class ModelAlgorithmConfig(BaseModel):
    """
    Algorithm configuration and parameters.

    Defines the computational algorithm with factors, weights,
    and execution parameters for contract-driven behavior.
    """

    algorithm_type: str = Field(
        ...,
        description="Algorithm type identifier",
        min_length=1,
    )

    factors: dict[str, ModelAlgorithmFactorConfig] = Field(
        ...,
        description="Algorithm factors with configuration",
    )

    normalization_method: str = Field(
        default="min_max",
        description="Global normalization method",
    )

    precision_digits: int = Field(
        default=6,
        description="Precision for floating point calculations",
        ge=1,
        le=15,
    )

    @field_validator("factors")
    @classmethod
    def validate_factor_weights_sum(
        cls,
        v: dict[str, ModelAlgorithmFactorConfig],
    ) -> dict[str, ModelAlgorithmFactorConfig]:
        """Validate that factor weights sum to approximately 1.0."""
        total_weight = sum(factor.weight for factor in v.values())
        if not (0.99 <= total_weight <= 1.01):
            msg = f"Factor weights must sum to 1.0, got {total_weight}"
            raise ValueError(msg)
        return v


class ModelParallelConfig(BaseModel):
    """
    Parallel processing configuration.

    Defines thread pools, async settings, and concurrency
    parameters for performance optimization.
    """

    enabled: bool = Field(default=True, description="Enable parallel processing")

    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads",
        ge=1,
        le=32,
    )

    batch_size: int = Field(
        default=100,
        description="Batch size for parallel operations",
        ge=1,
    )

    async_enabled: bool = Field(
        default=False,
        description="Enable asynchronous processing",
    )

    thread_pool_type: str = Field(
        default="ThreadPoolExecutor",
        description="Thread pool implementation type",
    )

    queue_size: int = Field(
        default=1000,
        description="Maximum queue size for pending operations",
        ge=1,
    )


class ModelCachingConfig(BaseModel):
    """
    Caching strategy and policies.

    Defines caching behavior for expensive computations
    with TTL, size limits, and eviction policies.
    """

    strategy: str = Field(
        default="lru",
        description="Caching strategy (lru, fifo, lfu)",
    )

    max_size: int = Field(
        default=1000,
        description="Maximum cache size (number of entries)",
        ge=1,
    )

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cache entries in seconds",
        ge=1,
    )

    enabled: bool = Field(default=True, description="Enable caching")

    cache_key_strategy: str = Field(
        default="input_hash",
        description="Strategy for generating cache keys",
    )

    eviction_policy: str = Field(
        default="least_recently_used",
        description="Eviction policy when cache is full",
    )


class ModelInputValidationConfig(BaseModel):
    """
    Input validation and transformation rules.

    Defines validation rules, constraints, and transformation
    logic for input data processing.
    """

    strict_validation: bool = Field(
        default=True,
        description="Enable strict input validation",
    )

    required_fields: list[str] = Field(
        default_factory=list,
        description="Required input fields",
    )

    field_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Field-specific validation constraints",
    )

    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Input transformation rules",
    )

    sanitization_enabled: bool = Field(
        default=True,
        description="Enable input sanitization",
    )


class ModelOutputTransformationConfig(BaseModel):
    """
    Output transformation and formatting rules.

    Defines transformation logic, formatting rules, and
    post-processing configuration for output data.
    """

    format_type: str = Field(default="standard", description="Output format type")

    precision_control: bool = Field(
        default=True,
        description="Enable precision control for numeric outputs",
    )

    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Output transformation rules",
    )

    validation_enabled: bool = Field(
        default=True,
        description="Enable output validation before return",
    )


class ModelContractCompute(ModelContractBase, MixinLazyEvaluation):
    """
    Contract model for NodeCompute implementations - Clean Architecture.

    Specialized contract for pure computation nodes using subcontract composition
    for clean separation between node logic and functionality patterns.
    Supports algorithm specifications, parallel processing, and caching via subcontracts.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    def __init__(self, **data):
        """Initialize compute contract with lazy evaluation capabilities."""
        super().__init__(**data)
        MixinLazyEvaluation.__init__(self)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation ensuring lazy evaluation mixin is initialized."""
        # Ensure lazy evaluation mixin is initialized (critical for YAML deserialization)
        if not hasattr(self, "_lazy_cache"):
            MixinLazyEvaluation.__init__(self)

        # Call parent post-init validation
        super().model_post_init(__context)

    node_type: Literal["COMPUTE"] = Field(
        default="COMPUTE",
        description="Node type classification for 4-node architecture",
    )

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

    validation_rules: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Validation rules in flexible format",
    )

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
        original_contract_data: dict | None = None,
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
        original_contract_data: dict | None = None,
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
            # Lazy evaluation to reduce memory usage by ~60%
            lazy_contract_data = self.lazy_model_dump()
            contract_data = lazy_contract_data()
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
    def from_yaml(cls, yaml_content: str) -> "ModelContractCompute":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractCompute: Validated contract model instance
        """
        from pydantic import ValidationError

        from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

        try:
            # Use safe YAML loader to parse content and validate as model
            return load_yaml_content_as_model(yaml_content, cls)

        except ValidationError as e:
            raise ValueError(f"Contract validation failed: {e}") from e
