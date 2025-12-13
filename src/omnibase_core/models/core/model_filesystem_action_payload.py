"""
Filesystem Action Payload Model.

Payload for filesystem actions (scan, watch, sync).
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelFilesystemActionPayload(ModelActionPayloadBase):
    """Payload for filesystem actions (scan, watch, sync)."""

    path: str | None = Field(default=None, description="Filesystem path to operate on")
    patterns: list[str] = Field(
        default_factory=list,
        description="File patterns to match",
    )
    recursive: bool = Field(default=False, description="Whether to operate recursively")
    follow_symlinks: bool = Field(
        default=False,
        description="Whether to follow symbolic links",
    )

    @field_validator("action_type")
    @classmethod
    def validate_filesystem_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid filesystem action."""
        if v.name not in ["scan", "watch", "sync"]:
            msg = f"Invalid filesystem action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
