import uuid
from typing import Dict, Generic, TypeVar

from pydantic import Field

"""
Model Compute Output - Output model for NodeCompute operations.

Strongly typed output wrapper that includes computation
metadata and performance metrics.
"""

from typing import Any, Dict, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

T_Output = TypeVar("T_Output")


class ModelComputeOutput(BaseModel, Generic[T_Output]):
    """
    Output model for NodeCompute operations.

    Strongly typed output wrapper that includes computation
    metadata and performance metrics.
    """

    result: T_Output
    operation_id: UUID
    computation_type: str
    processing_time_ms: float
    cache_hit: bool = False
    parallel_execution_used: bool = False
    metadata: dict[str, ModelSchemaValue] | None = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
