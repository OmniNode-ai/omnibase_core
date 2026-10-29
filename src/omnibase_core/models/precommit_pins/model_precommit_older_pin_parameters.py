# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Policy and message templates for multi-revision groups."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPrecommitOlderPinParameters(BaseModel):
    """Policy and message templates for multi-revision groups."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook_repos: tuple[str, ...] = Field(min_length=1)
    remediation: str = Field(min_length=1)
    older_message: str = Field(min_length=1)
    unresolved_message: str = Field(min_length=1)
