# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Policy for revisions whose time cannot be resolved."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPrecommitUnresolvedPinParameters(BaseModel):
    """Policy for revisions whose time cannot be resolved."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    remediation: str = Field(min_length=1)
