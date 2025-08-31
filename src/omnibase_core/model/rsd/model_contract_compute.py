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

from typing import Literal

from pydantic import BaseModel, Field, validator

from omnibase_core.enums.node import EnumNodeType
from omnibase_core.model.rsd.model_contract_base import ModelContractBase


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

    @validator("factors")
    def validate_factor_weights_sum(self, v):
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


class ModelContractCompute(ModelContractBase):
    """
    Contract model for NodeCompute implementations.

    Specialized contract for pure computation nodes with algorithm
    specifications, parallel processing, and caching strategies.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.COMPUTE] = EnumNodeType.COMPUTE

    # Computation configuration
    algorithm: ModelAlgorithmConfig = Field(
        ...,
        description="Algorithm configuration and parameters",
    )

    parallel_processing: ModelParallelConfig = Field(
        default_factory=ModelParallelConfig,
        description="Parallel execution configuration",
    )

    caching: ModelCachingConfig = Field(
        default_factory=ModelCachingConfig,
        description="Caching strategy and policies",
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

    def validate_node_specific_config(self) -> None:
        """
        Validate compute node-specific configuration requirements.

        Validates algorithm configuration, parallel processing settings,
        and caching policies for compute node compliance.

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

        # Validate caching configuration
        if self.caching.enabled and self.caching.max_size < 1:
            msg = "Caching requires positive max_size"
            raise ValueError(msg)

        # Validate performance requirements for compute nodes
        if not self.performance.single_operation_max_ms:
            msg = "Compute nodes must specify single_operation_max_ms performance requirement"
            raise ValueError(
                msg,
            )

    @validator("algorithm")
    def validate_algorithm_consistency(self, v):
        """Validate algorithm configuration consistency."""
        if v.algorithm_type == "weighted_factor_algorithm" and not v.factors:
            msg = "Weighted factor algorithm requires at least one factor"
            raise ValueError(msg)
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "forbid"
        use_enum_values = True
        validate_assignment = True
