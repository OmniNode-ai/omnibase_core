# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A reference to a threshold policy by id, version and digest (OMN-21999).

A view contract that names a policy carries this reference; the policy refuses a
reference whose digest is not the digest it computes
(``ModelViewThresholdPolicy.verify_pin``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_id_patterns import (
    ViewDigest,
    ViewId,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelViewThresholdPolicyPin"]


class ModelViewThresholdPolicyPin(BaseModel):
    """Policy id, version and the digest the referrer pins."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy_id: ViewId = Field(..., description="Identifier of the pinned policy")
    policy_version: ModelSemVer = Field(..., description="Pinned policy version")
    policy_digest: ViewDigest = Field(
        ...,
        description="Pinned digest of the policy, as 'sha256:<64 lowercase hex>'",
    )
