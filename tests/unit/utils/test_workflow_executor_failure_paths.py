# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Workflow executor failure path tests (OMN-12387).

Targets uncovered branches in util_workflow_executor.py (score 1.8, 1380 NLOC)
that are not covered by test_workflow_executor.py or test_workflow_executor_critical.py:

- validate_workflow_definition: returns error strings for duplicate step_ids,
  unknown dependency ids, and circular dependencies
- execute_workflow: empty step list, single step, disabled step, priority clamping,
  wave boundary not in actions, dependent step after its dependency
- get_execution_order: single step, independent steps, dependent chain

All functions use the correct async/sync API signatures. validate_workflow_definition
returns list[str] (not raises). execute_workflow and validate_workflow_definition are
both async. get_execution_order is sync and takes list[ModelWorkflowStep].

No new silent fallbacks.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
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
    execute_workflow,
    get_execution_order,
    validate_workflow_definition,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — match the pattern from test_workflow_executor.py
# ---------------------------------------------------------------------------


def _semver() -> ModelSemVer:
    return ModelSemVer(major=1, minor=0, patch=0)


def _make_step(
    step_id: UUID | None = None,
    name: str = "step",
    step_type: str = "compute",
    depends_on: list[UUID] | None = None,
    enabled: bool = True,
    priority: int = 100,
) -> ModelWorkflowStep:
    """Create a ModelWorkflowStep via model_construct (matches existing test patterns)."""
    return ModelWorkflowStep.model_construct(
        correlation_id=uuid4(),
        step_id=step_id or uuid4(),
        step_name=name,
        step_type=step_type,
        timeout_ms=30000,
        retry_count=3,
        enabled=enabled,
        skip_on_failure=False,
        continue_on_error=False,
        error_action="stop",
        max_memory_mb=None,
        max_cpu_percent=None,
        priority=priority,
        order_index=0,
        depends_on=depends_on if depends_on is not None else [],
        parallel_group=None,
        max_parallel_instances=1,
    )


def _make_workflow_def(
    execution_mode: str = "sequential",
    timeout_ms: int = 300_000,
) -> ModelWorkflowDefinition:
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=_semver(),
            version=_semver(),
            description="Test workflow for OMN-12387 coverage.",
            execution_mode=execution_mode,
            timeout_ms=timeout_ms,
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=_semver(),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=_semver(),
        ),
        version=_semver(),
    )


# ---------------------------------------------------------------------------
# validate_workflow_definition — returns list[str] of error messages
# ---------------------------------------------------------------------------


class TestValidateWorkflowDefinitionErrors:
    """validate_workflow_definition returns non-empty error list for invalid workflows."""

    @pytest.mark.asyncio
    async def test_empty_steps_returns_no_errors(self) -> None:
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [])
        assert errors == []

    @pytest.mark.asyncio
    async def test_valid_single_step_returns_no_errors(self) -> None:
        step = _make_step()
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [step])
        assert errors == []

    @pytest.mark.asyncio
    async def test_duplicate_step_ids_returns_error(self) -> None:
        shared_id = uuid4()
        s1 = _make_step(step_id=shared_id, name="step1")
        s2 = _make_step(step_id=shared_id, name="step2")
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [s1, s2])
        assert len(errors) > 0
        assert any("duplicate" in e.lower() for e in errors)

    @pytest.mark.asyncio
    async def test_unknown_dependency_id_returns_error(self) -> None:
        phantom_id = uuid4()
        step = _make_step(depends_on=[phantom_id])
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [step])
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_circular_dependency_returns_error(self) -> None:
        id_a = uuid4()
        id_b = uuid4()
        step_a = _make_step(step_id=id_a, name="a", depends_on=[id_b])
        step_b = _make_step(step_id=id_b, name="b", depends_on=[id_a])
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [step_a, step_b])
        assert len(errors) > 0
        assert any("cycle" in e.lower() or "circular" in e.lower() for e in errors)

    @pytest.mark.asyncio
    async def test_linear_dependency_chain_is_valid(self) -> None:
        id_a = uuid4()
        id_b = uuid4()
        step_a = _make_step(step_id=id_a, name="a")
        step_b = _make_step(step_id=id_b, name="b", depends_on=[id_a])
        step_c = _make_step(name="c", depends_on=[id_b])
        wf = _make_workflow_def()
        errors = await validate_workflow_definition(wf, [step_a, step_b, step_c])
        assert errors == []


# ---------------------------------------------------------------------------
# execute_workflow — basic paths
# ---------------------------------------------------------------------------


class TestExecuteWorkflowBasicPaths:
    """execute_workflow covers sequential success paths."""

    @pytest.mark.asyncio
    async def test_empty_steps_returns_completed(self) -> None:
        wf = _make_workflow_def()
        result = await execute_workflow(wf, [], uuid4())
        assert result.execution_status == EnumWorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_empty_steps_has_no_actions(self) -> None:
        wf = _make_workflow_def()
        result = await execute_workflow(wf, [], uuid4())
        assert result.actions_emitted == []

    @pytest.mark.asyncio
    async def test_single_enabled_step_produces_one_action(self) -> None:
        wf = _make_workflow_def()
        step = _make_step(name="deploy")
        result = await execute_workflow(wf, [step], uuid4())
        assert result.execution_status == EnumWorkflowStatus.COMPLETED
        assert len(result.actions_emitted) == 1

    @pytest.mark.asyncio
    async def test_single_disabled_step_has_no_actions(self) -> None:
        wf = _make_workflow_def()
        step = _make_step(name="skipped", enabled=False)
        result = await execute_workflow(wf, [step], uuid4())
        # Disabled steps are skipped
        assert result.actions_emitted == []

    @pytest.mark.asyncio
    async def test_three_independent_steps_produce_three_actions(self) -> None:
        wf = _make_workflow_def()
        steps = [_make_step(name=f"s{i}") for i in range(3)]
        result = await execute_workflow(wf, steps, uuid4())
        assert len(result.actions_emitted) == 3

    @pytest.mark.asyncio
    async def test_step_priority_clamped_to_10(self) -> None:
        """ModelWorkflowStep.priority=999 → action priority ≤ 10 (step vs action priority)."""
        wf = _make_workflow_def()
        step = _make_step(name="high_pri", priority=999)
        result = await execute_workflow(wf, [step], uuid4())
        for action in result.actions_emitted:
            assert action.priority <= 10, (
                f"Action priority {action.priority} exceeds 10 (step priority=999)"
            )

    @pytest.mark.asyncio
    async def test_wave_boundary_not_in_actions(self) -> None:
        """Wave boundary markers must not appear in actions_emitted (Fix 51)."""
        wf = _make_workflow_def()
        steps = [_make_step(name=f"s{i}") for i in range(4)]
        result = await execute_workflow(wf, steps, uuid4())
        for action in result.actions_emitted:
            # action_type is an EnumActionType — compare against its name/value
            action_type_str = action.action_type.value.lower()
            assert "wave_boundary" not in action_type_str, (
                f"Wave boundary leaked into actions: {action.action_type!r}"
            )

    @pytest.mark.asyncio
    async def test_workflow_id_propagated_to_result(self) -> None:
        wf = _make_workflow_def()
        wf_id = uuid4()
        result = await execute_workflow(wf, [], wf_id)
        assert result.workflow_id == wf_id

    @pytest.mark.asyncio
    async def test_dependent_step_emits_after_dependency(self) -> None:
        """Steps with depends_on appear after their dependency in emitted actions."""
        wf = _make_workflow_def()
        id_a = uuid4()
        id_b = uuid4()
        step_a = _make_step(step_id=id_a, name="first")
        step_b = _make_step(step_id=id_b, name="second", depends_on=[id_a])
        result = await execute_workflow(wf, [step_a, step_b], uuid4())
        assert len(result.actions_emitted) == 2
        # completed_steps is a list[str] (UUID strings) in execution order
        completed_ids = result.completed_steps
        assert str(id_a) in completed_ids
        assert str(id_b) in completed_ids
        assert completed_ids.index(str(id_a)) < completed_ids.index(str(id_b))


# ---------------------------------------------------------------------------
# get_execution_order — topological ordering
# ---------------------------------------------------------------------------


class TestGetExecutionOrder:
    """get_execution_order returns step IDs in topological dependency order."""

    def test_empty_steps_returns_empty(self) -> None:
        order = get_execution_order([])
        assert order == []

    def test_single_step_returned(self) -> None:
        step = _make_step()
        order = get_execution_order([step])
        assert order == [step.step_id]

    def test_three_independent_steps_all_returned(self) -> None:
        steps = [_make_step(name=f"s{i}") for i in range(3)]
        order = get_execution_order(steps)
        assert len(order) == 3
        for step in steps:
            assert step.step_id in order

    def test_dependency_precedes_dependent(self) -> None:
        id_a = uuid4()
        id_b = uuid4()
        step_a = _make_step(step_id=id_a, name="a")
        step_b = _make_step(step_id=id_b, name="b", depends_on=[id_a])
        order = get_execution_order([step_a, step_b])
        assert order.index(id_a) < order.index(id_b)

    def test_linear_chain_ordered_correctly(self) -> None:
        id_a, id_b, id_c = uuid4(), uuid4(), uuid4()
        step_a = _make_step(step_id=id_a, name="a")
        step_b = _make_step(step_id=id_b, name="b", depends_on=[id_a])
        step_c = _make_step(step_id=id_c, name="c", depends_on=[id_b])
        order = get_execution_order([step_a, step_b, step_c])
        assert order == [id_a, id_b, id_c]
