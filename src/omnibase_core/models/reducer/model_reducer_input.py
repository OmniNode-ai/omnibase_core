"""
Input model for NodeReducer operations.

This module provides the ModelReducerInput generic model that wraps data
reduction operations with comprehensive configuration for streaming modes,
conflict resolution, and batch processing.

Thread Safety:
    ModelReducerInput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.
    This follows the same pattern as ModelComputeInput.

Key Features:
    - Generic type parameter T_Input for type-safe data lists
    - Multiple reduction types (SUM, COUNT, GROUP_BY, etc.)
    - Configurable conflict resolution strategies
    - Streaming mode support (BATCH, WINDOWED, CONTINUOUS)
    - Time-based windowing for streaming operations

Example:
    >>> from omnibase_core.models.reducer import ModelReducerInput
    >>> from omnibase_core.enums.enum_reducer_types import (
    ...     EnumReductionType,
    ...     EnumConflictResolution,
    ...     EnumStreamingMode,
    ... )
    >>>
    >>> # Batch aggregation with fold reduction
    >>> input_data = ModelReducerInput(
    ...     data=[1, 2, 3, 4, 5],
    ...     reduction_type=EnumReductionType.FOLD,
    ...     conflict_resolution=EnumConflictResolution.MERGE,
    ... )
    >>>
    >>> # Streaming window with 5-second batches
    >>> streaming_input = ModelReducerInput(
    ...     data=[{"user": "alice", "count": 1}],
    ...     reduction_type=EnumReductionType.GROUP,
    ...     streaming_mode=EnumStreamingMode.WINDOWED,
    ...     window_size_ms=5000,
    ... )

See Also:
    - omnibase_core.models.reducer.model_reducer_output: Corresponding output model
    - omnibase_core.nodes.node_reducer: NodeReducer implementation
    - docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md: Reducer node tutorial
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata


class ModelReducerInput[T_Input](BaseModel):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations with
    comprehensive configuration for streaming modes, conflict resolution,
    and batch processing. Used by NodeReducer to aggregate and transform
    data collections.

    Type Parameters:
        T_Input: The type of elements in the data list. Can be any type
            including primitives, dictionaries, or Pydantic models.

    Attributes:
        data: List of input elements to reduce. Type is determined by the
            generic parameter T_Input.
        reduction_type: Type of reduction to perform (FOLD, ACCUMULATE, MERGE,
            AGGREGATE, GROUP, etc.). Determines the reduction algorithm.
        operation_id: Unique identifier for tracking this operation.
            Auto-generated UUID by default.
        conflict_resolution: Strategy for resolving conflicts when keys overlap.
            Options include FIRST_WINS, LAST_WINS, MERGE, ERROR, CUSTOM.
            Defaults to LAST_WINS.
        streaming_mode: Mode for processing data (BATCH, WINDOWED, CONTINUOUS).
            BATCH processes all data at once. WINDOWED uses time-based windows.
            Defaults to BATCH.
        batch_size: Maximum number of elements to process in each batch.
            Only relevant for BATCH mode. Defaults to 1000.
        window_size_ms: Window duration in milliseconds for WINDOWED mode.
            Data is aggregated within each window. Defaults to 5000 (5 seconds).
        metadata: Typed metadata for tracking and correlation (source, trace_id,
            correlation_id, group_key, partition_id, window_id, tags).
        timestamp: When this input was created. Auto-generated to current time.

    Example:
        >>> # Group operation with custom conflict resolution
        >>> input_data = ModelReducerInput[dict](
        ...     data=[{"key": "a", "value": 1}, {"key": "a", "value": 2}],
        ...     reduction_type=EnumReductionType.GROUP,
        ...     conflict_resolution=EnumConflictResolution.MERGE,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        # arbitrary_types_allowed: Required for generic type parameter T_Input which can be
        # any user-defined type (Pydantic models, dataclasses, custom classes, etc.) that
        # Pydantic cannot automatically serialize without this setting.
        arbitrary_types_allowed=True,
        # from_attributes: Required for pytest-xdist compatibility. Workers import classes
        # independently, and without this setting Pydantic may reject valid instances due to
        # class identity differences across worker processes.
        from_attributes=True,
    )

    data: list[T_Input]
    reduction_type: EnumReductionType
    operation_id: UUID = Field(default_factory=uuid4)
    conflict_resolution: EnumConflictResolution = EnumConflictResolution.LAST_WINS
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batch_size: int = Field(default=1000, gt=0, le=10000)
    window_size_ms: int = Field(default=5000, ge=1000, le=60000)
    metadata: ModelReducerMetadata = Field(default_factory=ModelReducerMetadata)
    timestamp: datetime = Field(default_factory=datetime.now)
