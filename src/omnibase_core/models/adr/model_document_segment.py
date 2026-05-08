# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Document segment model for ADR extraction pipeline (OMN-10691)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.adr.enum_segment_type import EnumSegmentType


class ModelDocumentSegment(BaseModel):
    """A bounded region of source text with a classified semantic role.

    segment_id is deterministic: sha256(source_path + source_content_sha256
    + start_line + end_line + segment_type).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: deterministic sha256 hex digest, not a UUID
    segment_id: str = Field(
        default="", description="Deterministic sha256 segment identifier"
    )
    source_path: str = Field(description="Repo-relative path to the source document")
    segment_type: EnumSegmentType = Field(
        description="Semantic classification of this segment"
    )
    content: str = Field(description="Raw text content of the segment")
    source_content_sha256: str = Field(
        description="SHA256 of the entire source document"
    )
    segment_content_sha256: str = Field(description="SHA256 of this segment's content")
    start_line: int = Field(ge=1, description="1-based start line in source document")
    end_line: int = Field(ge=1, description="1-based end line in source document")
    git_sha: str = Field(description="Git commit SHA at extraction time")
    created_at: datetime = Field(description="Timestamp when segment was first created")
    updated_at: datetime = Field(description="Timestamp when segment was last updated")
    subsystems: list[str] = Field(default_factory=list, description="Subsystem tags")
    tags: list[str] = Field(default_factory=list, description="Freeform tags")

    @model_validator(mode="after")
    def _compute_segment_id(self) -> ModelDocumentSegment:
        if not self.segment_id:
            raw = (
                f"{self.source_path}"
                f"{self.source_content_sha256}"
                f"{self.start_line}"
                f"{self.end_line}"
                f"{self.segment_type.value}"
            )
            computed = hashlib.sha256(raw.encode()).hexdigest()
            object.__setattr__(self, "segment_id", computed)
        return self


__all__ = ["ModelDocumentSegment"]
