# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkflowRequirement — implementation requirement recorded during SPEC."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowRequirement(BaseModel):
    """A single implementation requirement recorded during the SPEC phase."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="")
    statement: str = Field(default="")
    rationale: str = Field(default="")
    acceptance: list[str] = Field(default_factory=list)


__all__ = ["ModelWorkflowRequirement"]
