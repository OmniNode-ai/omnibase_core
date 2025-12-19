"""
Output model for NodeReducer operations.

Strongly typed output wrapper with reduction statistics, conflict resolution metadata,
and projection emission for pure fold operations.

Option A Semantics (OMN-941):
    Reducers are PURE FOLDS - they compute new state from events without side effects.
    - ALLOWED: projections[] - materialized view updates (primary output)
    - FORBIDDEN: events[] - reducers cannot emit events (use orchestrator)
    - FORBIDDEN: intents[] - reducers cannot emit intents (use orchestrator)

    The `intents` field is DEPRECATED and will be removed in v0.5.0.
    Use orchestrator nodes for intent-based side effects.

Thread Safety:
    ModelReducerOutput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.
    This follows the same pattern as ModelComputeOutput.

"""

import math
import warnings
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.projection.model_projection_base import ModelProjectionBase
from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelReducerOutput[T_Output](BaseModel):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics,
    conflict resolution metadata, and projection emission list.

    Option A Pure Fold Semantics (OMN-941):
        Reducers are PURE FOLDS - they deterministically compute new state from
        events without side effects. This ensures:
        - Replay safety: Same events always produce same state
        - Testability: No mocking required for side effects
        - Predictability: State transitions are deterministic

        ALLOWED outputs:
        - result: The new state after reduction (primary output)
        - projections[]: Materialized view updates for read optimization

        FORBIDDEN outputs (use Orchestrator instead):
        - events[]: Reducers cannot emit new events
        - intents[]: Reducers cannot emit side effect intents

    Thread Safety:
        This model is immutable (frozen=True) after creation. The projections tuple
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
        projections: Projection updates emitted during reduction. These are materialized
            view updates for read-optimized queries (Option A primary output).
        intents: DEPRECATED in v0.4.0, removed in v0.5.0. Reducers are pure folds and
            cannot emit side effect intents. Use Orchestrator nodes for intent-based
            workflows. Emits DeprecationWarning if non-empty.
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

    # Projection emission for pure fold pattern (Option A primary output)
    projections: tuple[ModelProjectionBase, ...] = Field(
        default=(),
        description=(
            "Projection updates emitted during reduction. These are materialized view "
            "updates for read-optimized queries. Primary output for Option A pure fold "
            "semantics where reducers compute state without side effects."
        ),
    )

    # DEPRECATED: Intent emission - violates Option A pure fold semantics
    intents: tuple[ModelIntent, ...] = Field(
        default=(),
        description=(
            "DEPRECATED in v0.4.0, will be removed in v0.5.0. "
            "Reducers are pure folds per Option A semantics (OMN-941) and cannot emit "
            "side effect intents. Use Orchestrator nodes for intent-based workflows. "
            "A DeprecationWarning is emitted if this field contains any intents."
        ),
        deprecated=True,
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

    @model_validator(mode="after")
    def warn_on_deprecated_intents(self) -> "ModelReducerOutput[T_Output]":
        """Emit deprecation warning if intents field is used.

        Per Option A semantics (OMN-941), reducers are pure folds and cannot emit
        side effect intents. This validator emits a DeprecationWarning when the
        deprecated intents field contains any values.

        The intents field will be removed in v0.5.0. Use Orchestrator nodes for
        intent-based side effect workflows.

        Returns:
            self: The validated model instance (unmodified)
        """
        if self.intents:
            warnings.warn(
                "ModelReducerOutput.intents is deprecated in v0.4.0 and will be removed "
                "in v0.5.0. Reducers are pure folds per Option A semantics (OMN-941) and "
                "cannot emit side effect intents. Use Orchestrator nodes for intent-based "
                f"workflows. Found {len(self.intents)} intent(s) that should be moved to "
                "an Orchestrator.",
                DeprecationWarning,
                stacklevel=2,
            )
        return self
