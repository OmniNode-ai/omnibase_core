# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Channel attachment model for OmniClaw normalized messaging."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelChannelAttachment(BaseModel):
    """Attachment metadata for a channel message.

    Represents a file or media attachment from any messaging platform,
    normalized into a common schema.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    filename: str = Field(..., min_length=1, description="Attachment filename")
    content_type: str = Field(..., min_length=1, description="MIME type")
    url: str | None = Field(default=None, description="Download URL if available")
    size_bytes: int | None = Field(default=None, description="File size in bytes")
