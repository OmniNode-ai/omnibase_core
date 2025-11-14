"""
Output model for NodeCompute operations.

Provides strongly typed output wrapper with computation metadata and performance metrics.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T_Output = TypeVar("T_Output")

__all__ = [
    "ModelComputeOutput",
]


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
    metadata: dict[str, Any] = Field(default_factory=dict)
