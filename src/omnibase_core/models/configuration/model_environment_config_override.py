# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Environment Config Override Model for ONEX Configuration System.

Strongly typed model for environment variable configuration override results.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEnvironmentConfigOverride(BaseModel):
    """Typed configuration override result from environment variables."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    default_mode: str | None = Field(
        default=None,
        description="Default mode override from environment",
    )
