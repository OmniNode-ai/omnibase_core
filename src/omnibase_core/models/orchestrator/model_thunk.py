import uuid
from typing import List

from pydantic import Field

"""
Thunk Model - ONEX Standards Compliant.

Deferred execution unit with metadata for workflow orchestration.
Converted from NamedTuple to Pydantic BaseModel for better validation.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_execution import EnumThunkType


class ModelThunk(BaseModel):
    """
    Deferred execution unit with metadata.

    Represents a unit of work that can be executed later,
    enabling lazy evaluation and workflow composition.

    Converted from NamedTuple to Pydantic BaseModel for:
    - Runtime validation
    - Better type safety
    - Serialization support
    - Default value handling
    """

    thunk_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this thunk",
    )

    thunk_type: EnumThunkType = Field(
        default=...,
        description="Type of thunk for execution routing",
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for thunk execution",
        min_length=1,
        max_length=100,
    )

    operation_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data payload for the operation",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of thunk IDs this thunk depends on",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for thunk execution",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when thunk was created",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
