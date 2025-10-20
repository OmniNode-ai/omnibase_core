"""
Action Model - ONEX Standards Compliant.

Orchestrator-issued Action with lease semantics for single-writer guarantees.
Converted from NamedTuple to Pydantic BaseModel for better validation.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_execution import EnumActionType


class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Represents an Action emitted by the Orchestrator to Compute/Reducer nodes
    with single-writer semantics enforced via lease_id and epoch.

    Converted from NamedTuple to Pydantic BaseModel for:
    - Runtime validation
    - Better type safety
    - Serialization support
    - Default value handling
    - Lease validation
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action",
    )

    action_type: EnumActionType = Field(
        default=...,
        description="Type of action for execution routing",
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for action execution",
        min_length=1,
        max_length=100,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Action payload data",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of action IDs this action depends on",
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

    # Lease management fields for single-writer semantics
    lease_id: UUID = Field(
        default=...,
        description="Lease ID proving Orchestrator ownership",
    )

    epoch: int = Field(
        default=...,
        description="Monotonically increasing version number",
        ge=0,
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for action execution",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when action was created",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
