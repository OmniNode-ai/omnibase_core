"""
Strongly typed models for extracted metadata blocks, decoupled from model_node_metadata.py to avoid circular imports.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock


class ModelExtractedBlock(BaseModel):
    """
    Result model for extract_block protocol method.
    """

    metadata: "NodeMetadataBlock | None" = Field(
        default=None,
        description="Extracted metadata block (NodeMetadataBlock or None)",
    )
    body: str | None = Field(
        default=None,
        description="File content with metadata block removed",
    )


# Compatibility alias
ExtractedBlockModel = ModelExtractedBlock

# NOTE: model_rebuild() is not called here to avoid circular import issues.
# If runtime forward reference resolution is needed, call ModelExtractedBlock.model_rebuild() after all models are loaded (e.g., in CLI entrypoint or test setup).
