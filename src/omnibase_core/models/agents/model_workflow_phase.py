# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Workflow phase model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelWorkflowPhase(BaseModel):
    """Single workflow phase definition.

    Represents a phase within a workflow template with its
    associated function and sub-phases.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    function_name: str | None = None
    phases: list[str] | None = None


__all__ = ["ModelWorkflowPhase"]
