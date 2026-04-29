# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanaryTierAssignments — canary tier assignment root model — OMN-10250.

Ported from onex_change_control.canary.schema (Wave 3).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from omnibase_core.models.governance.model_canary_tier import ModelCanaryTier


class ModelCanaryTierAssignments(BaseModel):
    version: Literal["1.0"]
    tiers: list[ModelCanaryTier]


__all__ = ["ModelCanaryTierAssignments"]
