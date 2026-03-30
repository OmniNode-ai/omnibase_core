# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelProbeResult: Result of probing a backend for readiness."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_probe_state import EnumProbeState


class ModelProbeResult(BaseModel):
    """Result of probing a backend for readiness."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state: EnumProbeState
    protocol_name: str
    backend_name: str
    package: str = Field(default="local")
    message: str = Field(default="")
