"""
Output model for NodeEffect operations.

This module provides the ModelEffectOutput model that wraps side effect
operation results with comprehensive transaction status, timing metrics,
and execution metadata for observability and error recovery.

Thread Safety:
    ModelEffectOutput is mutable by default but should be treated as
    immutable after creation for thread-safe access.

Key Features:
    - Transaction state tracking (COMMITTED, ROLLED_BACK, etc.)
    - Processing time measurement for performance analysis
    - Retry count tracking for debugging and alerting
    - Side effect and rollback operation audit trails
    - Metadata for custom tracking and correlation

Example:
    >>> from omnibase_core.models.effect import ModelEffectOutput
    >>> from omnibase_core.enums.enum_effect_types import (
    ...     EnumEffectType,
    ...     EnumTransactionState,
    ... )
    >>> from uuid import uuid4
    >>>
    >>> # Successful database operation result
    >>> output = ModelEffectOutput(
    ...     result={"rows_affected": 1},
    ...     operation_id=uuid4(),
    ...     effect_type=EnumEffectType.DATABASE_OPERATION,
    ...     transaction_state=EnumTransactionState.COMMITTED,
    ...     processing_time_ms=45.2,
    ...     side_effects_applied=["insert_user_record"],
    ... )

See Also:
    - omnibase_core.models.effect.model_effect_input: Corresponding input model
    - omnibase_core.nodes.node_effect: NodeEffect implementation
    - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumEffectType, EnumTransactionState
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata
from omnibase_core.types.type_effect_result import EffectResultType

__all__ = ["ModelEffectOutput"]


class ModelEffectOutput(BaseModel):
    """
    Output model for NodeEffect operations.

    Strongly typed output wrapper containing the operation result along with
    transaction status, timing metrics, and execution audit trail. Created
    by NodeEffect after executing side effect operations.

    Attributes:
        result: The operation result data. Type varies based on effect_type
            (e.g., query results for database reads, response body for API calls).
        operation_id: UUID from the corresponding ModelEffectInput. Enables
            correlation between input and output for tracing and debugging.
        effect_type: Type of side effect operation that was executed.
        transaction_state: Current state of the transaction (COMMITTED, ROLLED_BACK,
            PENDING, etc.). Indicates whether the operation was successfully applied.
        processing_time_ms: Actual execution time in milliseconds. Includes all
            retries and transaction overhead.
        retry_count: Number of FAILED ATTEMPTS before success or final failure.
            This semantic counts "how many times did we fail" rather than "how many
            retries did we perform", which is useful for metrics and debugging to
            understand the reliability of the operation.

            Semantic definition:
                - Success on first try: retry_count = 0
                - Failed once, succeeded on retry: retry_count = 1
                - Failed twice, succeeded on second retry: retry_count = 2
                - Failed all attempts (max_retries exhausted): retry_count = max_retries + 1

            Note: This differs from "retries_performed" which would be one less than
            retry_count (since the first attempt isn't a "retry"). See the error
            context in MixinEffectExecution._execute_with_retry for both values.
        side_effects_applied: List of side effect identifiers that were successfully
            applied. Useful for audit trails and debugging.
        rollback_operations: List of rollback operation identifiers if transaction
            was rolled back. Empty list if transaction succeeded.
        metadata: Additional context metadata from the operation. May include
            effect-specific information like row counts or API response codes.
        timestamp: When this output was created. Auto-generated to current time.

    Example:
        >>> # Check operation result
        >>> if output.transaction_state == EnumTransactionState.COMMITTED:
        ...     print(f"Success: {output.result}")
        ...     print(f"Time: {output.processing_time_ms:.2f}ms")
        ... else:
        ...     print(f"Rolled back: {output.rollback_operations}")
    """

    result: EffectResultType
    operation_id: UUID
    effect_type: EnumEffectType
    transaction_state: EnumTransactionState
    processing_time_ms: float
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of failed attempts before success or final failure. "
        "0 = success on first try, 1 = failed once then succeeded, etc.",
    )
    side_effects_applied: list[str] = Field(default_factory=list)
    rollback_operations: list[str] = Field(default_factory=list)
    metadata: ModelEffectMetadata = Field(default_factory=ModelEffectMetadata)
    timestamp: datetime = Field(default_factory=datetime.now)
