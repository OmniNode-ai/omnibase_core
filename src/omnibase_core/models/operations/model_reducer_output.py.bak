import uuid
from typing import Generic, TypeVar

from pydantic import Field

"""Reducer output model for data aggregation results."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_reduction_type import EnumReductionType
from omnibase_core.enums.enum_streaming_mode import EnumStreamingMode

from .model_config import ModelConfig

T_Output = TypeVar("T_Output")


class ModelReducerOutput(BaseModel, Generic[T_Output]):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics
    and conflict resolution metadata.
    """

    result: T_Output
    operation_id: UUID
    reduction_type: EnumReductionType
    processing_time_ms: float
    items_processed: int
    conflicts_resolved: int = 0
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batches_processed: int = 1
    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
