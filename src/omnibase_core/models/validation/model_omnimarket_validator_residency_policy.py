# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Scan policy of the omnimarket validator residency checker (OMN-21503).

Every path, name pattern and severity here is read from the validator's
.validation.yaml contract; the checker holds none as a literal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity

__all__ = ["ModelOmnimarketValidatorResidencyPolicy"]


class ModelOmnimarketValidatorResidencyPolicy(BaseModel):
    """What counts as a resident validator, and how strictly gaps are judged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    script_globs: tuple[str, ...] = Field(
        description="fnmatch globs over repository-relative script paths"
    )
    node_root: str = Field(description="Repository-relative directory holding nodes")
    node_name_patterns: tuple[str, ...] = Field(
        description="Regexes (fullmatch) over node directory names"
    )
    child_ticket_severity: EnumSeverity = Field(
        description="Severity of a validator entry that has no child ticket"
    )
    acceptance_wave: int = Field(
        ge=0, description="Wave whose acceptance requires the baseline at zero"
    )
    wave_obligation: str = Field(
        description="Obligation id the acceptance wave's manifest must carry"
    )
