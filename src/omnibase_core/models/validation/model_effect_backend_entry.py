# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEffectBackendEntry (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEffectBackendEntry(BaseModel):
    """The verdict on one effect node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_name: str
    path: str
    has_in_memory_default: bool
    has_real_backend_overlay: bool
    in_memory_factory: str = Field(
        default="", description="Dotted path of the in-memory factory"
    )
    real_factory: str = Field(
        default="", description="Dotted path of the real-backend factory"
    )
    overlay_key: str = Field(
        default="", description="Overlay key that chooses the real backend"
    )
    scenario: str = Field(
        default="", description="Dotted path of the suite scenario the effect declares"
    )

    @property
    def on_both(self) -> bool:
        return self.has_in_memory_default and self.has_real_backend_overlay
