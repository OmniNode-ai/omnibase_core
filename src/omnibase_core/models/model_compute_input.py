"""
ModelComputeInput - Strongly typed input model for NodeCompute operations.

Provides type-safe input wrapper with metadata tracking for computation operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = [
    "ModelComputeInput",
]


class ModelComputeInput[T_Input](BaseModel):
    """
    Input model for NodeCompute operations.

    Strongly typed input wrapper that ensures type safety
    and provides metadata for computation tracking.
    """

    data: T_Input
    operation_id: UUID = Field(default_factory=uuid4)
    computation_type: str = "default"
    cache_enabled: bool = True
    parallel_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
