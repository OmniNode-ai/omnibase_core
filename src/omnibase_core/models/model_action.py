"""
ModelAction - Orchestrator-issued command with lease semantics.

Represents an Action emitted by the Orchestrator to Compute/Reducer nodes
with single-writer semantics enforced via lease_id and epoch.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_orchestrator_types import EnumActionType


class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Actions carry proof of ownership (lease_id) and version control (epoch)
    to prevent concurrent modification conflicts.
    """

    action_id: UUID = Field(..., description="Unique action identifier (UUID)")
    action_type: EnumActionType = Field(..., description="Type of action for routing")
    target_node_type: str = Field(..., description="Target node type for execution")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Action payload data"
    )
    dependencies: list[UUID] = Field(
        default_factory=list, description="List of dependency action IDs (UUIDs)"
    )
    priority: int = Field(
        default=1, description="Execution priority (higher = more urgent)"
    )
    timeout_ms: int = Field(
        default=30000, description="Execution timeout in milliseconds"
    )

    # Lease management fields for single-writer semantics
    lease_id: UUID = Field(..., description="Lease ID proving Orchestrator ownership")
    epoch: int = Field(..., description="Monotonically increasing version number")

    retry_count: int = Field(default=0, description="Number of retry attempts")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Action creation timestamp"
    )
