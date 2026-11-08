# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEffectBackendsReport (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_effect_backend_entry import (
    ModelEffectBackendEntry,
)


class ModelEffectBackendsReport(BaseModel):
    """Every effect node judged against the two-backend rule; lists are sorted by node name.

    The lists and counts are filled by the handler from ``entries`` so the JSON form carries them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: tuple[ModelEffectBackendEntry, ...] = ()
    unreadable: tuple[str, ...] = ()
    effects_total: int = 0
    without_in_memory_default: tuple[str, ...] = ()
    not_on_both: tuple[str, ...] = ()
    on_both: tuple[str, ...] = ()
    not_on_both_count: int = 0
    inventory_available: bool = Field(
        default=True,
        description="False when the scan root could not be read; the lists are then not an inventory",
    )
    root_unavailable: str = Field(
        default="",
        description="Why the scan root could not be read; empty when the inventory was scanned",
    )
