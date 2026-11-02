# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The outcome of a value that falls in no band of a policy (OMN-21999).

It is a result in its own type, not a severity: no band means no verdict, and the
renderer shows the value as out-of-band rather than inventing one.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_id_patterns import (
    ViewDigest,
    ViewId,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelViewThresholdOutOfBand"]


class ModelViewThresholdOutOfBand(BaseModel):
    """A value in no band, with the policy revision that found it so."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy_id: ViewId = Field(..., description="Policy that was evaluated")
    policy_version: ModelSemVer = Field(..., description="Version of that policy")
    policy_digest: ViewDigest = Field(
        ...,
        description="Digest of that policy revision, as 'sha256:<hex>'",
    )
    mapped_field: str = Field(
        ..., min_length=1, description="Mapped field the policy reads"
    )
    value: float = Field(
        ...,
        allow_inf_nan=True,
        description="The value that fell in no band; may be NaN or infinite",
    )
