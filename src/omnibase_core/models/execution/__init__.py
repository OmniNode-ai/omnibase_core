# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
ONEX Execution Models Module.

This module provides the data models for the Runtime Execution Sequencing Model,
including phase steps and execution plans.

Example:
    >>> from omnibase_core.models.execution import ModelPhaseStep, ModelExecutionPlan
    >>> from omnibase_core.enums import EnumHandlerExecutionPhase
    >>>
    >>> step = ModelPhaseStep(
    ...     phase=EnumHandlerExecutionPhase.EXECUTE,
    ...     handler_ids=["handler_a", "handler_b"]
    ... )
    >>> plan = ModelExecutionPlan(phases=[step])

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep

__all__ = [
    "ModelPhaseStep",
    "ModelExecutionPlan",
]
