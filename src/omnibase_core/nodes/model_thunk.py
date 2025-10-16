"""
ModelThunk - Deferred execution unit with metadata.

Represents a unit of work that can be executed later,
enabling lazy evaluation and workflow composition.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.nodes.enum_orchestrator_types import EnumThunkType


class ModelThunk(BaseModel):
    """
    Deferred execution unit with metadata.

    Represents a unit of work that can be executed later,
    enabling lazy evaluation and workflow composition.
    """

    thunk_id: UUID = Field(..., description="Unique thunk identifier (UUID)")
    thunk_type: EnumThunkType = Field(..., description="Type of thunk for routing")
    target_node_type: str = Field(..., description="Target node type for execution")
    operation_data: dict[str, Any] = Field(
        default_factory=dict, description="Data for the operation"
    )
    dependencies: list[UUID] = Field(
        default_factory=list, description="List of dependency thunk IDs (UUIDs)"
    )
    priority: int = Field(
        default=1, description="Execution priority (higher = more urgent)"
    )
    timeout_ms: int = Field(
        default=30000, description="Execution timeout in milliseconds"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Thunk creation timestamp"
    )
