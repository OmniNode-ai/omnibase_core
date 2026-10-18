# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Workflow text and explicit exception text supplied at the effect boundary."""

from pydantic import BaseModel, ConfigDict, Field


class ModelSharedTokenPolicyRequest(BaseModel):
    """The policy reads secret names only; it never resolves credentials."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflows: dict[str, str] = Field(min_length=1)
    allowlist: str = "entries: []\n"
