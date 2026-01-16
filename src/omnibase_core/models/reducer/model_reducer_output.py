"""
Output model for NodeReducer operations.

Strongly typed output wrapper with reduction statistics, conflict resolution metadata,
and Intent emission for pure FSM pattern.

Thread Safety:
    ModelReducerOutput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.
    This follows the same pattern as ModelComputeOutput.

"""

import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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

    Negative Value Semantics (CRITICAL):
        This model uses sentinel values to distinguish between normal operation
        and error/unavailable states WITHOUT raising exceptions. This design allows
        the reducer to complete successfully even when certain metrics cannot be
        measured, avoiding cascading failures.

        processing_time_ms sentinel behavior:
            - >= 0.0: Normal operation - measured execution time in milliseconds
            - -1.0: Sentinel value - timing measurement failed or unavailable
            - Other negative values: INVALID - will raise ValidationError

        items_processed sentinel behavior:
            - >= 0: Normal operation - actual count of items processed
            - -1: Sentinel value - count unavailable due to error
            - Other negative values: INVALID - will raise ValidationError

        Why -1 specifically?
            - Common programming convention for "not found" or "unavailable"
            - Easily distinguishable from valid counts/times (always non-negative)
            - Single sentinel value simplifies validation and error handling
            - Prevents confusion with other negative values that might represent
              different error conditions

        Alternative Design Considered:
            Using Optional[float] / Optional[int] with None for unavailable values.
            Rejected because:
                1. None doesn't distinguish between "not measured" vs "measurement failed"
                2. Requires callers to handle None in addition to numeric values
                3. -1 sentinel is more explicit and self-documenting
                4. Maintains consistency with common C/POSIX conventions

    Attributes:
        result: The new state after reduction (type determined by T_Output).
        operation_id: UUID from the corresponding ModelReducerInput for correlation.
        reduction_type: Type of reduction performed (FOLD, ACCUMULATE, MERGE, etc.).
        processing_time_ms: Execution time in milliseconds. Uses sentinel pattern:
            -1.0 = timing measurement failed/unavailable (DO NOT use for errors),
            >= 0.0 = actual measured time.
            See "Negative Value Semantics" section above for full rationale and usage guide.
        items_processed: Number of items processed. Uses sentinel pattern:
            -1 = count unavailable due to error (DO NOT use for validation failures),
            >= 0 = actual item count.
            See "Negative Value Semantics" section above for full rationale and usage guide.
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
        # arbitrary_types_allowed: Required for generic type parameter T_Output which can be
        # any user-defined type (Pydantic models, dataclasses, custom classes, etc.) that
        # Pydantic cannot automatically serialize without this setting.
        arbitrary_types_allowed=True,
        # from_attributes: Required for pytest-xdist compatibility. Workers import classes
        # independently, and without this setting Pydantic may reject valid instances due to
        # class identity differences across worker processes.
        from_attributes=True,
    )

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType

    # Performance metrics - only -1 sentinel permitted for error signaling
    processing_time_ms: float = Field(
        description=(
            "Execution time in milliseconds. Uses sentinel pattern: "
            "-1.0 = timing measurement failed/unavailable (sentinel), "
            ">= 0.0 = actual measured time. "
            "See class docstring 'Negative Value Semantics' for full details."
        )
    )
    items_processed: int = Field(
        description=(
            "Number of items processed during reduction. Uses sentinel pattern: "
            "-1 = count unavailable due to error (sentinel), "
            ">= 0 = actual item count. "
            "See class docstring 'Negative Value Semantics' for full details."
        )
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

    @field_validator("processing_time_ms")
    @classmethod
    def validate_processing_time_ms(cls, v: float) -> float:
        """Validate processing_time_ms follows sentinel pattern and rejects special float values.

        Enforces that:
        1. Special float values (NaN, Inf, -Inf) are ALWAYS rejected
        2. Negative values are ONLY -1.0 (sentinel for unavailable/failed)
        3. Any other negative value is invalid

        Args:
            v: The processing time value to validate

        Returns:
            The validated processing time value

        Raises:
            ModelOnexError: If value is NaN, Inf, -Inf, or negative but not exactly -1.0
        """
        # Reject special float values first (NaN, Inf, -Inf)
        if math.isnan(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="processing_time_ms cannot be NaN (not a number)",
                context={"value": str(v), "field": "processing_time_ms"},
            )
        if math.isinf(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"processing_time_ms cannot be {'positive' if v > 0 else 'negative'} infinity",
                context={"value": str(v), "field": "processing_time_ms"},
            )

        # Enforce sentinel pattern: only -1.0 is permitted as negative value
        if v < 0.0 and v != -1.0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"processing_time_ms must be >= 0.0 or exactly -1.0 (sentinel), got {v}",
                context={
                    "value": v,
                    "field": "processing_time_ms",
                    "sentinel_value": -1.0,
                },
            )
        return v

    @field_validator("items_processed")
    @classmethod
    def validate_items_processed(cls, v: int) -> int:
        """Validate items_processed follows sentinel pattern.

        Enforces that negative values are ONLY -1 (sentinel for unavailable/error).
        Any other negative value is invalid.

        Note: Integer validation does not require special float value checks (NaN, Inf)
        because Pydantic will reject those during int coercion. This validator only
        enforces the sentinel pattern for negative integers.

        Args:
            v: The items processed count to validate

        Returns:
            The validated items processed count

        Raises:
            ModelOnexError: If value is negative but not exactly -1
        """
        # Enforce sentinel pattern: only -1 is permitted as negative value
        if v < 0 and v != -1:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"items_processed must be >= 0 or exactly -1 (sentinel), got {v}",
                context={
                    "value": v,
                    "field": "items_processed",
                    "sentinel_value": -1,
                },
            )
        return v
