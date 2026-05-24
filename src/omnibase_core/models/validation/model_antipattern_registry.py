# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternRegistry — versioned collection of antipattern entries (OMN-11910)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)


class ModelAntipatternRegistry(BaseModel):
    """Versioned registry of antipattern detection entries."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: str = Field(description="Registry schema version, e.g. '1.0.0'")
    last_updated: datetime = Field(description="Timestamp of the last registry update")
    entries: tuple[ModelAntipatternEntry, ...] = Field(
        default=(),
        description="All antipattern entries in this registry",
    )


__all__ = ["ModelAntipatternRegistry"]
