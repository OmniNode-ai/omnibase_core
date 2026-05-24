# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternOverrideConfig — per-repo antipattern override config (OMN-11912)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)
from omnibase_core.models.validation.model_antipattern_entry_override import (
    ModelAntipatternEntryOverride,
)


class ModelAntipatternOverrideConfig(BaseModel):
    """Per-repo antipattern configuration read from .onex/antipattern-overrides.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overrides: list[ModelAntipatternEntryOverride] = Field(
        default_factory=list,
        description="Field-level overrides for existing antipattern entries",
    )
    custom_entries: list[ModelAntipatternEntry] = Field(
        default_factory=list,
        description="New antipattern entries to append to the registry",
    )


__all__ = ["ModelAntipatternOverrideConfig"]
