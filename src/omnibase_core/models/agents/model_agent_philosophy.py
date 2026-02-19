# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent philosophy model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.typed_dict_methodology import TypedDictMethodology


class ModelAgentPhilosophy(BaseModel):
    """Agent philosophy and guiding principles.

    Defines the core mission, principles, and methodology that guide
    the agent's behavior and decision-making.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    core_responsibility: str = Field(..., description="Primary mission statement")
    core_purpose: str | None = None
    principles: list[str] | None = None
    design_philosophy: list[str] | None = None
    methodology: TypedDictMethodology | None = None
    context_philosophy: list[str] | None = None


__all__ = ["ModelAgentPhilosophy"]
