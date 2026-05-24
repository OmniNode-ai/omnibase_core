# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternEntryOverride — per-repo override for a single antipattern entry (OMN-11912)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelAntipatternEntryOverride(BaseModel):
    """A per-repo override for an existing antipattern entry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Antipattern name to override")
    severity: Literal["ERROR", "WARNING", "INFO"] | None = Field(
        default=None, description="Override severity (None = keep default)"
    )
    enforcement: Literal["blocking", "advisory", "informational"] | None = Field(
        default=None, description="Override enforcement level (None = keep default)"
    )
    enabled: bool | None = Field(
        default=None,
        description="Set False to disable this antipattern for the repo (None = keep default)",
    )
    file_globs: list[str] | None = Field(
        default=None, description="Override file globs (None = keep default)"
    )


__all__ = ["ModelAntipatternEntryOverride"]
