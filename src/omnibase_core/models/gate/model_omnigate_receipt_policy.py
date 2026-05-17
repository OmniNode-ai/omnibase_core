# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate receipt policy model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.gate.model_omnigate_identity_policy import (
    ModelOmniGateIdentityPolicy,
)


class ModelOmniGateReceiptPolicy(BaseModel):
    """Policy for receipt freshness, signing, and blocking semantics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_age_minutes: int = Field(default=120, gt=0)
    max_receipt_bytes: int = Field(default=65536, gt=0, le=262144)
    require_diff_binding: bool = Field(default=True)
    signing: str = Field(default="sigstore")
    allow_unsigned: bool = Field(default=False)
    advisory_blocks: bool = Field(default=False)
    identity: ModelOmniGateIdentityPolicy | None = None


__all__ = ["ModelOmniGateReceiptPolicy"]
