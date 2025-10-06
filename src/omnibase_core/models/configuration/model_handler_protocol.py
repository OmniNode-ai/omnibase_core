from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_handler_source import EnumHandlerSource
from omnibase_core.models.metadata.model_semver import ModelSemVer

from .model_can_handle_result import ModelCanHandleResult
from .model_serialized_block import ModelSerializedBlock

CanHandleResultModel = ModelCanHandleResult
SerializedBlockModel = ModelSerializedBlock


class ModelHandlerMetadata(BaseModel):
    """
    Canonical metadata for a file type handler.
    """

    handler_name: str = Field(..., description="Handler name.")
    handler_version: ModelSemVer = Field(..., description="Handler version.")
    handler_author: str = Field(..., description="Handler author.")
    handler_description: str = Field(..., description="Handler description.")
    supported_extensions: list[str] = Field(
        default_factory=list,
        description="Supported file extensions.",
    )
    supported_filenames: list[str] = Field(
        default_factory=list,
        description="Supported special filenames.",
    )
    handler_priority: int = Field(
        ...,
        description="Handler priority (higher = preferred).",
    )
    requires_content_analysis: bool = Field(
        ...,
        description="Whether handler requires content analysis.",
    )
    source: EnumHandlerSource = Field(
        ...,
        description="Handler source (core, plugin, runtime, etc.)",
    )


# Compatibility alias
HandlerModelMetadata = ModelHandlerMetadata
