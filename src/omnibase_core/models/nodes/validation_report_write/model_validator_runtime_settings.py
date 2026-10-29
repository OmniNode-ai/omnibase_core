# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The validator-runtime settings file of the report-write node (OMN-21529)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRuntimeSettings"]


class ModelValidatorRuntimeSettings(BaseModel):
    """Overlay path, default report path and repository the runtime falls back to."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    default_overlay: str = Field(
        min_length=1, description="Overlay file, relative to the node package."
    )
    default_report_path: str = Field(
        min_length=1,
        description="Report path used when --report-json is omitted; '{validator_id}' expands.",
    )
    default_repository: str = Field(
        min_length=1, description="Repository named on triggered events unless given."
    )
    run_topic: str = Field(
        min_length=1, description="Topic the one run event per run is published on."
    )
