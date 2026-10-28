# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data for the pre-commit pin-parity check (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPrecommitPinRules"]


class ModelPrecommitPinRules(BaseModel):
    """Hook repositories whose entries must agree on their newest pin."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook_repos: tuple[str, ...] = Field(min_length=1)
