# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate check declaration model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_omnigate import EnumOmniGateCheckType


class ModelOmniGateCheck(BaseModel):
    """A maintainer-authored check declared in `.omnigate.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    run: str
    check_type: EnumOmniGateCheckType = Field(default=EnumOmniGateCheckType.SHELL)
    timeout_seconds: int = Field(default=300, gt=0, le=3600)
    allowed_env: tuple[str, ...] = Field(default=())
    advisory_is_blocking: bool = Field(default=False)


__all__ = ["ModelOmniGateCheck"]
