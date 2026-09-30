# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalDependencyIssuerBinding."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ModelGoalDependencyIssuerBinding(BaseModel):
    """Protected issuer authority for one sealed dependency identifier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dependency_id: str = Field(  # string-id-ok: stable manifest key
        ..., min_length=1, max_length=128
    )
    issuer_domain: str = Field(..., min_length=1, max_length=128)
