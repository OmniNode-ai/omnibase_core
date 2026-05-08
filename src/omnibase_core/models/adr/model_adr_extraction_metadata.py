# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ADR extraction metadata model capturing LLM provenance (OMN-10691)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelADRExtractionMetadata(BaseModel):
    """Metadata capturing the provenance of an ADR draft."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    model_id: str = Field(  # string-id-ok: LLM model name identifier, not a UUID
        description="LLM model ID used for extraction"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    pipeline_version: str = Field(  # string-version-ok: pipeline semver string
        description="ADR extraction pipeline version"
    )
    # string-id-ok: template name identifier, not a UUID
    prompt_template_id: str = Field(description="Prompt template identifier")
    prompt_template_version: str = Field(  # string-version-ok: template semver string
        description="Prompt template version"
    )
    canary_run_id: str = Field(  # string-id-ok: canary run name/slug, not a UUID
        description="Canary run identifier"
    )
    extracted_at: datetime = Field(description="Timestamp of extraction")


__all__ = ["ModelADRExtractionMetadata"]
