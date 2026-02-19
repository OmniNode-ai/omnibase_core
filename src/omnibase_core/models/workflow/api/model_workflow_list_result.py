# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field

from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_workflow import ModelWorkflow


class ModelWorkflowListResult(ModelBaseResult):
    workflows: list[ModelWorkflow] = Field(default_factory=list)
