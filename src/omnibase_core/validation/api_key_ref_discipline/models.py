# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic models for the api_key_ref_discipline COMPUTE validator (OMN-12878)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelApiKeyRefFinding",
    "ModelApiKeyRefScanInput",
    "ModelApiKeyRefScanResult",
]


class ModelApiKeyRefFinding(BaseModel):
    """A single api_key_env deprecation finding in a bifrost config."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: str = Field(description="Relative path of the scanned config file.")
    backend_id: str = Field(  # string-id-ok: bifrost backend_id is an external YAML slug, not an internal UUID
        description="Identifier of the offending backend entry (bifrost backend_id slug)."
    )
    deprecated_field: str = Field(
        description="The deprecated field name found (always 'api_key_env')."
    )
    message: str = Field(
        description=(
            "Human-readable violation message directing the author to use "
            "api_key_ref or secret_ref instead."
        )
    )


class ModelApiKeyRefScanInput(BaseModel):
    """Input payload for HandlerApiKeyRefDisciplineCompute.

    All file I/O is the EFFECT boundary's responsibility. The handler receives
    only pre-loaded content here (COMPUTE purity constraint).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_contents: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of relative-path → raw YAML text for all config files to scan."
        ),
    )


class ModelApiKeyRefScanResult(BaseModel):
    """Output from HandlerApiKeyRefDisciplineCompute."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: list[ModelApiKeyRefFinding] = Field(
        default_factory=list,
        description="All api_key_env deprecation findings across scanned files.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Parse/IO errors encountered during scanning.",
    )
    passed: bool = Field(description="True when there are no findings and no errors.")
