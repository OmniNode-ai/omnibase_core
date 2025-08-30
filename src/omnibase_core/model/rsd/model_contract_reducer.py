#!/usr/bin/env python3
"""
Reducer Contract Model - ONEX Standards Compliant.

Specialized contract model for NodeReducer implementations providing:
- Reduction operation specifications (fold, accumulate, merge algorithms)
- Streaming configuration for large datasets
- Conflict resolution strategies and merge policies
- Memory management for batch processing

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Literal

from omnibase.enums.enum_node_type import EnumNodeType
from pydantic import BaseModel, Field, validator

from omnibase_core.model.rsd.model_contract_base import ModelContractBase


class ModelReductionConfig(BaseModel):
    """
    Data reduction operation specifications.

    Defines reduction algorithms, aggregation functions,
    and data processing patterns for efficient data consolidation.
    """

    operation_type: str = Field(
        ...,
        description="Type of reduction operation (fold, accumulate, merge, aggregate, etc.)",
        min_length=1,
    )

    reduction_function: str = Field(
        ...,
        description="Reduction function identifier",
        min_length=1,
    )

    associative: bool = Field(
        default=True,
        description="Whether the reduction operation is associative",
    )

    commutative: bool = Field(
        default=False,
        description="Whether the reduction operation is commutative",
    )

    identity_element: str | None = Field(
        default=None,
        description="Identity element for the reduction operation",
    )

    chunk_size: int = Field(
        default=1000,
        description="Chunk size for batch reduction operations",
        ge=1,
    )

    parallel_enabled: bool = Field(
        default=True,
        description="Enable parallel reduction processing",
    )

    intermediate_results_caching: bool = Field(
        default=True,
        description="Cache intermediate reduction results",
    )


class ModelStreamingConfig(BaseModel):
    """
    Streaming configuration for large datasets.

    Defines streaming parameters, buffer management,
    and memory-efficient processing for large data volumes.
    """

    enabled: bool = Field(default=True, description="Enable streaming processing")

    buffer_size: int = Field(
        default=8192,
        description="Stream buffer size in bytes",
        ge=1024,
    )

    window_size: int = Field(
        default=1000,
        description="Processing window size for streaming operations",
        ge=1,
    )

    window_overlap: int = Field(
        default=0,
        description="Overlap between processing windows",
        ge=0,
    )

    memory_threshold_mb: int = Field(
        default=512,
        description="Memory threshold for streaming activation in MB",
        ge=1,
    )

    backpressure_enabled: bool = Field(
        default=True,
        description="Enable backpressure handling for streaming",
    )

    checkpoint_interval: int = Field(
        default=10000,
        description="Checkpoint interval for streaming operations",
        ge=1,
    )

    flow_control_enabled: bool = Field(
        default=True,
        description="Enable flow control for streaming",
    )

    @validator("window_overlap")
    def validate_window_overlap(self, v, values):
        """Validate window overlap is less than window size."""
        if "window_size" in values and v >= values["window_size"]:
            msg = "window_overlap must be less than window_size"
            raise ValueError(msg)
        return v


class ModelConflictResolutionConfig(BaseModel):
    """
    Conflict resolution strategies and merge policies.

    Defines conflict detection, resolution strategies,
    and merge policies for handling data conflicts during reduction.
    """

    strategy: str = Field(
        default="last_writer_wins",
        description="Conflict resolution strategy (last_writer_wins, first_writer_wins, merge, manual)",
    )

    detection_enabled: bool = Field(
        default=True,
        description="Enable automatic conflict detection",
    )

    detection_fields: list[str] = Field(
        default_factory=list,
        description="Fields to monitor for conflict detection",
    )

    merge_function: str | None = Field(
        default=None,
        description="Custom merge function for conflict resolution",
    )

    priority_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Priority weights for weighted conflict resolution",
    )

    timestamp_based_resolution: bool = Field(
        default=True,
        description="Use timestamps for conflict resolution",
    )

    conflict_logging_enabled: bool = Field(
        default=True,
        description="Enable detailed conflict logging",
    )

    manual_review_threshold: float = Field(
        default=0.9,
        description="Confidence threshold for manual review requirement",
        ge=0.0,
        le=1.0,
    )


class ModelMemoryManagementConfig(BaseModel):
    """
    Memory management for batch processing.

    Defines memory allocation, garbage collection,
    and resource management for efficient batch processing.
    """

    max_memory_mb: int = Field(
        default=1024,
        description="Maximum memory allocation in MB",
        ge=1,
    )

    gc_threshold: float = Field(
        default=0.8,
        description="Garbage collection trigger threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    memory_pool_enabled: bool = Field(
        default=True,
        description="Enable memory pooling for reusable objects",
    )

    lazy_loading_enabled: bool = Field(
        default=True,
        description="Enable lazy loading for large datasets",
    )

    spill_to_disk_enabled: bool = Field(
        default=True,
        description="Enable spilling to disk when memory is full",
    )

    spill_threshold: float = Field(
        default=0.9,
        description="Memory threshold for spilling to disk",
        ge=0.0,
        le=1.0,
    )

    compression_enabled: bool = Field(
        default=True,
        description="Enable compression for spilled data",
    )


class ModelAggregationConfig(BaseModel):
    """
    Data aggregation specifications.

    Defines aggregation functions, grouping strategies,
    and statistical computations for data consolidation.
    """

    aggregation_functions: list[str] = Field(
        ...,
        description="List of aggregation functions (sum, count, avg, min, max, etc.)",
        min_items=1,
    )

    grouping_fields: list[str] = Field(
        default_factory=list,
        description="Fields to group by for aggregation",
    )

    statistical_functions: list[str] = Field(
        default_factory=list,
        description="Statistical functions to compute (median, std, percentiles, etc.)",
    )

    precision_digits: int = Field(
        default=6,
        description="Precision for aggregated numeric values",
        ge=1,
        le=15,
    )

    null_handling_strategy: str = Field(
        default="ignore",
        description="Strategy for handling null values (ignore, include, error)",
    )

    duplicate_handling: str = Field(
        default="include",
        description="Strategy for handling duplicate values (include, unique, error)",
    )


class ModelContractReducer(ModelContractBase):
    """
    Contract model for NodeReducer implementations.

    Specialized contract for data aggregation nodes with reduction
    operations, streaming configuration, and conflict resolution.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    node_type: Literal[EnumNodeType.REDUCER] = EnumNodeType.REDUCER

    # Reduction configuration
    reduction_operations: list[ModelReductionConfig] = Field(
        ...,
        description="Data reduction operation specifications",
        min_items=1,
    )

    streaming: ModelStreamingConfig = Field(
        default_factory=ModelStreamingConfig,
        description="Streaming and memory management",
    )

    conflict_resolution: ModelConflictResolutionConfig = Field(
        default_factory=ModelConflictResolutionConfig,
        description="Conflict resolution strategies",
    )

    # Memory and performance management
    memory_management: ModelMemoryManagementConfig = Field(
        default_factory=ModelMemoryManagementConfig,
        description="Memory management for batch processing",
    )

    aggregation: ModelAggregationConfig = Field(
        ...,
        description="Data aggregation specifications",
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

    def validate_node_specific_config(self) -> None:
        """
        Validate reducer node-specific configuration requirements.

        Validates reduction operations, streaming configuration,
        and memory management for reducer node compliance.

        Raises:
            ValidationError: If reducer-specific validation fails
        """
        # Validate at least one reduction operation is defined
        if not self.reduction_operations:
            msg = "Reducer node must define at least one reduction operation"
            raise ValueError(
                msg,
            )

        # Validate aggregation functions are defined
        if not self.aggregation.aggregation_functions:
            msg = "Reducer node must define at least one aggregation function"
            raise ValueError(
                msg,
            )

        # Validate memory management consistency
        if (
            self.memory_management.spill_to_disk_enabled
            and self.memory_management.spill_threshold
            <= self.memory_management.gc_threshold
        ):
            msg = "Spill threshold must be greater than GC threshold"
            raise ValueError(msg)

        # Validate streaming configuration
        if self.streaming.enabled and self.streaming.window_size < 1:
            msg = "Streaming requires positive window_size"
            raise ValueError(msg)

        # Validate conflict resolution strategy
        if (
            self.conflict_resolution.strategy == "merge"
            and not self.conflict_resolution.merge_function
        ):
            msg = "Merge conflict resolution strategy requires merge_function"
            raise ValueError(
                msg,
            )

        # Validate performance requirements for reducer nodes
        if not self.performance.batch_operation_max_s:
            msg = "Reducer nodes must specify batch_operation_max_s performance requirement"
            raise ValueError(
                msg,
            )

    @validator("reduction_operations")
    def validate_reduction_operations_consistency(self, v):
        """Validate reduction operations configuration consistency."""
        # Check for conflicting associativity requirements
        associative_ops = [op for op in v if op.associative]
        non_associative_ops = [op for op in v if not op.associative]

        if associative_ops and non_associative_ops:
            # Mixed associativity is allowed but should be documented
            pass

        return v

    @validator("aggregation")
    def validate_aggregation_functions(self, v):
        """Validate aggregation functions are supported."""
        supported_functions = {
            "sum",
            "count",
            "avg",
            "min",
            "max",
            "median",
            "std",
            "var",
            "percentile",
            "mode",
            "first",
            "last",
            "unique_count",
        }

        for func in v.aggregation_functions:
            if func not in supported_functions:
                msg = f"Unsupported aggregation function: {func}"
                raise ValueError(msg)

        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "forbid"
        use_enum_values = True
        validate_assignment = True
