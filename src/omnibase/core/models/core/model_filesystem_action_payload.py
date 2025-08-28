"""
Filesystem Action Payload Model.

Payload for filesystem actions (scan, watch, sync).
"""

from typing import List, Optional

from pydantic import Field, field_validator

from omnibase.model.core.model_action_payload_base import ModelActionPayloadBase
from omnibase.model.core.model_node_action_type import ModelNodeActionType


class ModelFilesystemActionPayload(ModelActionPayloadBase):
    """Payload for filesystem actions (scan, watch, sync)."""

    path: Optional[str] = Field(None, description="Filesystem path to operate on")
    patterns: List[str] = Field(
        default_factory=list, description="File patterns to match"
    )
    recursive: bool = Field(default=False, description="Whether to operate recursively")
    follow_symlinks: bool = Field(
        default=False, description="Whether to follow symbolic links"
    )

    @field_validator("action_type")
    @classmethod
    def validate_filesystem_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid filesystem action."""
        if v.name not in ["scan", "watch", "sync"]:
            raise ValueError(f"Invalid filesystem action: {v.name}")
        return v
