import uuid
from typing import Dict, Generic, TypeVar

from pydantic import Field

"""
Model Compute Input - Input model for NodeCompute operations.

Strongly typed input wrapper that ensures type safety
and provides metadata for computation tracking.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

T_Input = TypeVar("T_Input")


class ModelComputeInput(BaseModel, Generic[T_Input]):
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
    metadata: dict[str, ModelSchemaValue] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(arbitrary_types_allowed=True)
