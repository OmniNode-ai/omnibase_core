# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strongly typed result for an extracted node metadata block."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock


class ModelExtractedBlock(BaseModel):
    """
    Result model for extract_block protocol method.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: ModelNodeMetadataBlock | None = Field(
        default=None,
        description="Extracted canonical node metadata block, when present",
    )
    body: str | None = Field(
        default=None,
        description="File content with metadata block removed",
    )


# Compatibility alias
ExtractedBlockModel = ModelExtractedBlock
