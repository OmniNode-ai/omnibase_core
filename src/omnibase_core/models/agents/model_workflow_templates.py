# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Workflow templates model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.agents.model_workflow_phase import ModelWorkflowPhase


class ModelWorkflowTemplates(BaseModel):
    """Workflow template definitions.

    Provides templates for standard workflow phases that agents
    can follow during execution.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    initialization: ModelWorkflowPhase | None = None
    intelligence_gathering: ModelWorkflowPhase | None = None
    task_execution: ModelWorkflowPhase | None = None
    context_execution: ModelWorkflowPhase | None = None
    knowledge_capture: ModelWorkflowPhase | None = None


__all__ = ["ModelWorkflowTemplates"]
