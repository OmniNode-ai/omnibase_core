# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The first record an app sends when rendering a view starts (OMN-21999).

The record binds the render start time to the view and the exact received
document, before a completed render record is available.
"""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_id_patterns import (
    ViewDigest,
    ViewId,
)

__all__ = ["ModelViewRenderStartedRecord"]


class ModelViewRenderStartedRecord(BaseModel):
    """Start time and document identity for one render attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    started_at: AwareDatetime = Field(
        ..., description="Time the app started rendering the document"
    )
    view_id: ViewId = Field(
        ...,
        description="Identifier of the rendered view",
    )
    source_document_digest: ViewDigest = Field(
        ...,
        description="Digest of the rendered document, as 'sha256:<64 lowercase hex>'",
    )
