# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI-mode override policy for model routing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCiOverridePolicy(BaseModel):
    """CI-mode override: when ONEX_CI_MODE=true, use this primary model key."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary: str = Field(..., description="model_id key to use in CI mode.")


__all__ = ["ModelCiOverridePolicy"]
