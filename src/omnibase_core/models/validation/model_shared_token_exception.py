# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Reviewed shared-token exceptions; no path globs or implicit exemptions."""

from pydantic import Field, field_validator

from omnibase_core.models.validation.model_shared_token_use import ModelSharedTokenUse


class ModelSharedTokenException(ModelSharedTokenUse):
    """An exception explains why the run token cannot serve this exact use."""

    reason: str = Field(min_length=20)

    @field_validator("workflow", "location", "reference", "reason")
    @classmethod
    def require_concrete_values(cls, value: str) -> str:
        """Refuse wildcard exceptions and reasons consisting only of whitespace."""
        if not value.strip() or any(char in value for char in ("*", "?")):
            raise ValueError("exceptions require concrete values without wildcards")
        return value
