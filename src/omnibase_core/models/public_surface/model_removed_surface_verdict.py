# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The verdict of the removed-surface gate."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.models.public_surface.model_gate_inputs_manifest import (
    ModelGateInputsManifest,
)
from omnibase_core.models.public_surface.model_public_surface_entry import (
    ModelPublicSurfaceEntry,
)


class ModelRemovedSurfaceVerdict(BaseModel):
    """PASSED, REFUSED or UNREAD, with the evidence each status requires."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: Literal["PASSED", "REFUSED", "UNREAD"]
    removed_entries: tuple[ModelPublicSurfaceEntry, ...] = ()
    consumers: dict[str, tuple[str, ...]] = {}
    unread_reads: tuple[str, ...] = ()
    inputs_manifest: ModelGateInputsManifest

    @model_validator(mode="after")
    def _status_needs_its_evidence(self) -> ModelRemovedSurfaceVerdict:
        if self.status == "UNREAD" and not self.unread_reads:
            raise ValueError("verdict UNREAD needs at least one unread read")
        if self.status == "REFUSED" and not any(self.consumers.values()):
            raise ValueError("verdict REFUSED needs at least one consumer")
        return self
