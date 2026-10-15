# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Werror coverage for effect workflow steps (OMN-17869).

An effect step maps to EnumActionType.EFFECT. The payload built for it must be
one ModelAction recommends for EFFECT, otherwise ModelAction emits an
informational UserWarning that becomes an exception under PYTHONWARNINGS=error
and marks a valid workflow failed.
"""

import warnings
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
)
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_workflow_executor import (
    _create_action_for_step,
    execute_workflow,
)


def _workflow_definition() -> ModelWorkflowDefinition:
    version = ModelSemVer(major=1, minor=0, patch=0)
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="effect_werror_workflow",
            workflow_version=version,
            version=version,
            description="Effect-step workflow run with warnings as errors",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(nodes=[], version=version),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=version,
        ),
        version=version,
    )


@pytest.mark.unit
class TestEffectStepWerror:
    """Effect steps must not emit a payload recommendation warning."""

    def test_effect_step_action_emits_no_warning(self) -> None:
        step = ModelWorkflowStep(step_name="Fetch Data", step_type="effect")

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            action, _ = _create_action_for_step(step, uuid4())

        assert action.action_type == EnumActionType.EFFECT

    @pytest.mark.asyncio
    async def test_sequential_effect_workflow_completes_under_werror(self) -> None:
        first = ModelWorkflowStep(step_name="Fetch Data", step_type="effect")
        second = ModelWorkflowStep(
            step_name="Save Results",
            step_type="effect",
            depends_on=[first.step_id],
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = await execute_workflow(
                _workflow_definition(),
                [first, second],
                uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert result.execution_status == EnumWorkflowStatus.COMPLETED
        assert len(result.completed_steps) == 2
        assert len(result.failed_steps) == 0

    @pytest.mark.asyncio
    async def test_parallel_effect_workflow_completes_under_werror(self) -> None:
        fetch = ModelWorkflowStep(step_name="Fetch Data", step_type="effect")
        left = ModelWorkflowStep(
            step_name="Write Left",
            step_type="effect",
            depends_on=[fetch.step_id],
        )
        right = ModelWorkflowStep(
            step_name="Write Right",
            step_type="effect",
            depends_on=[fetch.step_id],
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = await execute_workflow(
                _workflow_definition(),
                [fetch, left, right],
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        assert result.execution_status == EnumWorkflowStatus.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0
