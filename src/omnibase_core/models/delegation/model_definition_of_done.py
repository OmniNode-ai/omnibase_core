# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDefinitionOfDone: split-by-semantics DoD checks for task-class contracts (OMN-10614)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDefinitionOfDone(BaseModel):
    """DoD checks split by enforcement semantics.

    Deterministic checks BLOCK delegation result injection on failure.
    Heuristic checks MAY escalate or warn per escalation_policy — a heuristic
    pass is not proof of correctness and must not be represented as such.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    deterministic: list[str] = Field(default_factory=list)
    heuristic: list[str] = Field(default_factory=list)


__all__ = ["ModelDefinitionOfDone"]
