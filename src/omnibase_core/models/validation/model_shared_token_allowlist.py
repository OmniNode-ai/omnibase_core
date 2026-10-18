# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Strict schema for reviewed shared-token exceptions."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_shared_token_exception import (
    ModelSharedTokenException,
)


class ModelSharedTokenAllowlist(BaseModel):
    """No implicit exceptions or unknown policy fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entries: tuple[ModelSharedTokenException, ...]
