# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline models.

This module contains Pydantic models for the pipeline execution system.

Note: These models were moved from omnibase_core.pipeline.models to
omnibase_core.models.pipeline to comply with ONEX repository structure
validation that requires all models in src/omnibase_core/models/.

The ModelExecutionPlan class was renamed to ModelPipelineExecutionPlan
to avoid naming conflicts with omnibase_core.models.execution.ModelExecutionPlan.
Legacy aliases are provided for migration.
"""

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import (
    ModelPipelineContext,
    PipelineContext,
)
from omnibase_core.models.pipeline.model_pipeline_execution_plan import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineExecutionPlan,
    ModelPipelinePhaseExecutionPlan,
)
from omnibase_core.models.pipeline.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)
from omnibase_core.models.pipeline.model_pipeline_result import (
    ModelPipelineResult,
    PipelineResult,
)
from omnibase_core.models.pipeline.model_validation_warning import (
    ModelValidationWarning,
)

__all__ = [
    # New canonical names
    "ModelHookError",
    "ModelPipelineContext",
    "ModelPipelineExecutionPlan",
    "ModelPipelinePhaseExecutionPlan",
    "ModelPipelineHook",
    "ModelPipelineResult",
    "ModelValidationWarning",
    "PipelinePhase",
    # Legacy aliases
    "ModelExecutionPlan",
    "ModelPhaseExecutionPlan",
    "PipelineContext",
    "PipelineResult",
]
