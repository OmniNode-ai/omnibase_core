"""
Input model for NodeReducer operations.

Strongly typed input wrapper for data reduction operations with streaming
and conflict resolution configuration.

Author: ONEX Framework Team
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)

T_Input = TypeVar("T_Input")


class ModelReducerInput(BaseModel, Generic[T_Input]):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations
    with streaming and conflict resolution configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[T_Input]  # Strongly typed data list
    reduction_type: EnumReductionType
    operation_id: UUID = Field(default_factory=uuid4)
    conflict_resolution: EnumConflictResolution = EnumConflictResolution.LAST_WINS
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batch_size: int = 1000
    window_size_ms: int = 5000
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
