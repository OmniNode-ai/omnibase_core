# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternSummary — minimal antipattern projection for context injection (OMN-11928)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.context.model_context_provenance import ModelContextProvenance

__all__ = ["ModelAntipatternSummary"]


class ModelAntipatternSummary(BaseModel):
    """Minimal antipattern projection for context injection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Unique antipattern identifier")
    severity: Literal["ERROR", "WARNING", "INFO"] = Field(
        description="Violation severity"
    )
    category: Literal[
        "code_quality", "architecture", "security", "performance", "naming", "testing"
    ] = Field(description="Antipattern category")
    description: str = Field(description="Human-readable explanation")
    provenance: ModelContextProvenance = Field(description="Source provenance")
