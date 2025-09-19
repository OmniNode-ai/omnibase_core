"""
Conflict resolution configuration model for REDUCER nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumConflictResolutionStrategy


class ModelConflictResolutionConfig(BaseModel):
    """Conflict resolution configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: EnumConflictResolutionStrategy = Field(
        ...,
        description="Conflict resolution strategy for handling data conflicts",
    )
    merge_fields: list[str] | None = Field(
        None,
        description="Fields to merge in case of conflicts",
    )
    priority_field: str | None = Field(
        None,
        description="Field to use for priority-based resolution",
    )
