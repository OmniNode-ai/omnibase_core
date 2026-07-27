# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit, auditable non-exhaustive demand-sampling strategy.

OMN-15126 implementation of the OMN-14845 design (design §4 CORRECTION).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelSamplingPolicy"]


class ModelSamplingPolicy(BaseModel):
    """Explicit, auditable non-exhaustive sampling strategy (design §4 CORRECTION).

    ``None`` on the registry entry / receipt means "check every eligible
    item" (the default). This model is only populated when a surface's
    eligible-demand volume exceeds ``max_eligible_volume_before_sampling``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    strategy: Literal["deterministic_hash_stride", "reservoir"]
    min_sample_size: int = Field(..., ge=1)
    max_eligible_volume_before_sampling: int = Field(..., ge=1)
