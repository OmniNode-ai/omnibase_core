# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Decision extraction model for ADR extraction pipeline (OMN-10691)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.adr.enum_decision_type import EnumDecisionType


class ModelDecisionExtraction(BaseModel):
    """An architectural decision extracted from one or more document segments.

    extraction_id is deterministic: sha256(extraction_version + model_id
    + sorted(source_segment_ids) + sorted(segment_content_hashes)).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: deterministic sha256 hex digest, not a UUID
    extraction_id: str = Field(
        default="", description="Deterministic sha256 extraction identifier"
    )
    decision_type: EnumDecisionType = Field(
        description="Classification of the decision"
    )
    title: str = Field(description="Short human-readable decision title")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    rationale: list[str] = Field(
        default_factory=list, description="Supporting rationale statements"
    )
    subsystems: list[str] = Field(
        default_factory=list, description="Affected subsystems"
    )
    supersedes: list[str] = Field(
        default_factory=list, description="IDs of superseded decisions"
    )
    alternatives_considered: list[str] = Field(
        default_factory=list, description="Alternatives that were evaluated"
    )
    source_segment_ids: list[str] = Field(description="Segment IDs used as evidence")
    segment_content_hashes: list[str] = Field(
        description="Content hashes of source segments"
    )
    extraction_model_id: str = Field(  # string-id-ok: LLM model name, not a UUID
        description="LLM model ID used for extraction"
    )
    extraction_version: str = Field(  # string-version-ok: pipeline semver string
        description="Extraction pipeline version"
    )
    # string-id-ok: template name identifier, not a UUID
    prompt_template_id: str = Field(description="Prompt template identifier")
    prompt_template_version: str = Field(  # string-version-ok: template semver string
        description="Prompt template version"
    )
    extracted_at: datetime = Field(description="Timestamp of extraction")

    @model_validator(mode="after")
    def _compute_extraction_id(self) -> ModelDecisionExtraction:
        if not self.extraction_id:
            sorted_ids = sorted(self.source_segment_ids)
            sorted_hashes = sorted(self.segment_content_hashes)
            raw = (
                f"{self.extraction_version}"
                f"{self.extraction_model_id}"
                f"{''.join(sorted_ids)}"
                f"{''.join(sorted_hashes)}"
            )
            computed = hashlib.sha256(raw.encode()).hexdigest()
            object.__setattr__(self, "extraction_id", computed)
        return self


__all__ = ["ModelDecisionExtraction"]
