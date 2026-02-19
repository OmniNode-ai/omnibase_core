# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration points model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelIntegrationPoints(BaseModel):
    """Integration point definitions.

    Defines how the agent integrates with other agents and
    collaboration patterns.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    complementary_agents: list[str] | None = None
    collaboration_patterns: list[str] | None = None


__all__ = ["ModelIntegrationPoints"]
