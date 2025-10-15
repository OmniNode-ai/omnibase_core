import uuid
from typing import Generic, TypeVar

from pydantic import Field

"""Reducer input model for data aggregation operations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_conflict_resolution import EnumConflictResolution
from omnibase_core.enums.enum_reduction_type import EnumReductionType
from omnibase_core.enums.enum_streaming_mode import EnumStreamingMode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

T_INPUT = TypeVar("T_INPUT")


class ModelReducerInput(BaseModel, Generic[T_INPUT]):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations
    with streaming and conflict resolution configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    data: list[T_INPUT] = Field(default_factory=list)
    operation_id: UUID = Field(default_factory=uuid4)
    conflict_resolution: EnumConflictResolution = EnumConflictResolution.LAST_WINS
    streaming_mode: EnumStreamingMode = EnumStreamingMode.BATCH
    batch_size: int = 1000
    window_size_ms: int = 5000
    metadata: dict[str, ModelSchemaValue] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    # Additional fields for reducer operations
    reduction_type: EnumReductionType = Field(
        default=EnumReductionType.AGGREGATE,
        description="Type of reduction operation to perform",
    )
    reducer_function: str | None = Field(
        default=None, description="Name or path of the reducer function to use"
    )
    group_key: str | list[str] | None = Field(
        default=None, description="Field(s) to group by for grouped reductions"
    )
    accumulator_init: Any = Field(
        default=None, description="Initial value for accumulator operations"
    )
