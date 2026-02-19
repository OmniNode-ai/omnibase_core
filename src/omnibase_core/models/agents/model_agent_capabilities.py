# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent capabilities model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelAgentCapabilities(BaseModel):
    """Agent capability definitions.

    Specifies what the agent can do, organized by priority level.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    primary: list[str] = Field(..., description="Primary capabilities")
    secondary: list[str] | None = None
    specialized: list[str] | None = None


__all__ = ["ModelAgentCapabilities"]
