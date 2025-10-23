"""
Output model for NodeReducer operations.

Strongly typed output wrapper with reduction statistics, conflict resolution metadata,
and Intent emission for pure FSM pattern.

Author: ONEX Framework Team
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.model_intent import ModelIntent

T_Output = TypeVar("T_Output")


class ModelReducerOutput(BaseModel, Generic[T_Output]):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics,
    conflict resolution metadata, and Intent emission list.

    Pure FSM Pattern:
        result: The new state after reduction
        intents: Side effects to be executed by Effect node
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType
    processing_time_ms: float
    items_processed: int
    conflicts_resolved: int = 0
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batches_processed: int = 1

    # Intent emission for pure FSM pattern
    intents: list[ModelIntent] = Field(
        default_factory=list,
        description="Side effect intents emitted during reduction (for Effect node)",
    )

    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
