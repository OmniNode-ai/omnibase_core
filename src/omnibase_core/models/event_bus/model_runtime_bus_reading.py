# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""What the runtime writes into workflow_result.json under ``bus_reading``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_runtime_bus_binding_kind import EnumRuntimeBusBindingKind


class ModelRuntimeBusReading(BaseModel):
    """The runtime bus reading the runtime records for a workflow run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumRuntimeBusBindingKind
    degraded: bool
    reason: str | None = None
    forwarder: str | None = None
    events_recorded: int = Field(ge=0)
    events_forwarded: int = Field(default=0, ge=0)
    events_failed: int = Field(default=0, ge=0)


__all__: list[str] = ["ModelRuntimeBusReading"]
