# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Credential placeholders in ``~/.onex/config.yaml``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCliUserConfigCredentials(BaseModel):
    """Credential placeholders bootstrapped for a new install."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        frozen=True,
    )

    linear_api_key: str = Field(
        default="",
        alias="LINEAR_API_KEY",
        description="Linear API key; get one from https://linear.app/settings/api",
    )
    infisical_token: str = Field(
        default="",
        alias="INFISICAL_TOKEN",
        description="Infisical token; only required for Mode B (cloud-connected)",
    )


__all__ = ["ModelCliUserConfigCredentials"]
