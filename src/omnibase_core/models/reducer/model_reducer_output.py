"""
Output model for NodeReducer operations.

Strongly typed output wrapper with reduction statistics, conflict resolution metadata,
and Intent emission for pure FSM pattern.

Thread Safety:
    ModelReducerOutput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.
    This follows the same pattern as ModelComputeOutput.

"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelReducerOutput[T_Output](BaseModel):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics,
    conflict resolution metadata, and Intent emission list.

    Pure FSM Pattern:
        result: The new state after reduction
        intents: Side effects to be executed by Effect node

    Thread Safety:
        This model is immutable (frozen=True) after creation. The intents tuple
        and typed metadata are captured at construction time and cannot be modified.
        This ensures thread-safe sharing of output instances across concurrent
        readers without synchronization.

        For mutable workflows (rare), create a new ModelReducerOutput instance
        rather than modifying an existing one.

    Attributes:
        result: The new state after reduction (type determined by T_Output).
        operation_id: UUID from the corresponding ModelReducerInput for correlation.
        reduction_type: Type of reduction performed (FOLD, ACCUMULATE, MERGE, etc.).
        processing_time_ms: Actual execution time in milliseconds. Negative values are
            permitted to represent error conditions or unavailable timing data:
            - Normal: >= 0.0 (measured execution time)
            - Error sentinel: -1.0 (timing measurement failed)
            - Unknown: -1.0 (timing not available or not measured)
            This flexibility allows error handling without raising exceptions when timing
            is non-critical but the reduction result is valid.
        items_processed: Total number of items processed in the reduction. Negative values
            are permitted to represent error conditions or rollback scenarios:
            - Normal: >= 0 (actual count of items processed)
            - Error sentinel: -1 (count unavailable due to error)
            - Rollback: negative value (items rolled back or invalidated)
            This allows reporting processing state even when counts are uncertain or
            represent compensating operations.
        conflicts_resolved: Number of conflicts resolved during reduction (default 0).
        streaming_mode: Processing mode used (BATCH, WINDOWED, CONTINUOUS).
        batches_processed: Number of batches processed (default 1).
        intents: Side effect intents emitted during reduction for Effect node execution.
        metadata: Typed metadata for tracking and correlation (source, trace_id,
            correlation_id, group_key, partition_id, window_id, tags, trigger).
            Replaces dict[str, str] with ModelReducerMetadata for type safety.
        timestamp: When this output was created (auto-generated).

    Migration from dict[str, str] metadata:
        Before (v0.3.x):
            output = ModelReducerOutput(
                result=state,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=42.0,
                items_processed=10,
                metadata={"source": "api", "correlation_id": "abc123"}
            )

        After (v0.4.0+):
            output = ModelReducerOutput(
                result=state,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=42.0,
                items_processed=10,
                metadata=ModelReducerMetadata(
                    source="api",
                    correlation_id="abc123"
                )
            )

        The typed metadata provides compile-time type checking and better IDE support.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType

    # Performance metrics - negative values permitted for error signaling
    processing_time_ms: (
        float  # -1.0 = timing unavailable/failed, >= 0.0 = measured time
    )
    items_processed: (
        int  # -1 = count unavailable, negative = rollback, >= 0 = normal count
    )

    conflicts_resolved: int = 0
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batches_processed: int = 1

    # Intent emission for pure FSM pattern
    intents: tuple[ModelIntent, ...] = Field(
        default=(),
        description="Side effect intents emitted during reduction (for Effect node)",
    )

    metadata: ModelReducerMetadata = Field(
        default_factory=ModelReducerMetadata,
        description="Typed metadata for tracking and correlation (source, trace_id, "
        "correlation_id, group_key, partition_id, window_id, tags, trigger)",
    )
    timestamp: datetime = Field(default_factory=datetime.now)
