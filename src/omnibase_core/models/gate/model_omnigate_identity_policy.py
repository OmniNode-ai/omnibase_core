# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate Sigstore identity policy model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelOmniGateIdentityPolicy(BaseModel):
    """Trusted Sigstore identity policy from base-branch config."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_issuer: str
    allowed_identities: tuple[str, ...] = Field(default=())
    allowed_identity_regexes: tuple[str, ...] = Field(default=())


__all__ = ["ModelOmniGateIdentityPolicy"]
