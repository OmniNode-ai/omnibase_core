# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceCheck — a single check entry within a DoD evidence item. OMN-8916"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDodEvidenceCheck(BaseModel):
    """A single verifiable check within a DoD evidence item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: str = Field(..., min_length=1)
    check_value: str = Field(..., min_length=1)


__all__ = ["ModelDodEvidenceCheck"]
