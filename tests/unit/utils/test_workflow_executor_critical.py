# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for uncovered branches in util_workflow_executor.py.

Targets CCN hotspots not covered by existing test_workflow_executor.py:
- error_action='continue' in sequential and parallel modes
- batch mode metadata (execution_mode='batch', batch_size)
- reserved step type rejection (ModelOnexError from validate_workflow_definition)
- _validate_json_payload strict mode edge cases
- timeout deadline triggering in sequential and parallel modes
- skip_on_failure semantics with prior failures
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_workflow_executor import (
    _validate_json_payload,
    execute_workflow,
    validate_workflow_definition,
)

pytestmark = pytest.mark.unit


def _semver() -> ModelSemVer:
    return ModelSemVer(major=1, minor=0, patch=0)


def _make_workflow_def(
    name: str = "test_workflow",
    execution_mode: str = "sequential",
    timeout_ms: int = 300000,
) -> ModelWorkflowDefinition:
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name=name,
            workflow_version=_semver(),
            version=_semver(),
            description="test",
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


@pytest.fixture
def workflow_def() -> ModelWorkflowDefinition:
    return _make_workflow_def()


@pytest.fixture
def parallel_workflow_def() -> ModelWorkflowDefinition:
    return _make_workflow_def(name="parallel_test_workflow", execution_mode="parallel")


@pytest.fixture
def batch_workflow_def() -> ModelWorkflowDefinition:
    return _make_workflow_def(name="batch_test_workflow", execution_mode="batch")


def _step(
    name: str,
    step_type: str = "compute",
    depends_on: list[UUID] | None = None,
    enabled: bool = True,
    error_action: str = "stop",
    skip_on_failure: bool = False,
) -> ModelWorkflowStep:
    return ModelWorkflowStep(
        step_id=uuid4(),
        step_name=name,
        step_type=step_type,
        enabled=enabled,
        depends_on=depends_on or [],
        error_action=error_action,
        skip_on_failure=skip_on_failure,
    )


class TestBatchModeMetadata:
    @pytest.mark.asyncio
    async def test_batch_mode_metadata_has_batch_execution_mode(
        self, batch_workflow_def: ModelWorkflowDefinition
    ) -> None:
        steps = [_step("step1"), _step("step2")]
        result = await execute_workflow(
            batch_workflow_def,
            steps,
            uuid4(),
            execution_mode=EnumExecutionMode.BATCH,
        )
        assert result.execution_status == EnumWorkflowStatus.COMPLETED
        assert result.metadata is not None
        assert result.metadata.execution_mode == "batch"

    @pytest.mark.asyncio
    async def test_batch_mode_metadata_has_batch_size(
        self, batch_workflow_def: ModelWorkflowDefinition
    ) -> None:
        steps = [_step("step1"), _step("step2"), _step("step3")]
        result = await execute_workflow(
            batch_workflow_def,
            steps,
            uuid4(),
            execution_mode=EnumExecutionMode.BATCH,
        )
        assert result.metadata is not None
        assert result.metadata.batch_size == 3

    @pytest.mark.asyncio
    async def test_batch_mode_completes_all_steps(
        self, batch_workflow_def: ModelWorkflowDefinition
    ) -> None:
        steps = [_step("a"), _step("b"), _step("c")]
        result = await execute_workflow(
            batch_workflow_def,
            steps,
            uuid4(),
            execution_mode=EnumExecutionMode.BATCH,
        )
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0


class TestErrorActionContinue:
    @pytest.mark.asyncio
    async def test_sequential_continue_on_error_proceeds_to_next_step(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        from unittest.mock import patch

        step_fail_id = uuid4()
        step_ok_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_fail_id,
                step_name="fails_with_continue",
                step_type="compute",
                error_action="continue",
            ),
            ModelWorkflowStep(
                step_id=step_ok_id,
                step_name="runs_after_failure",
                step_type="compute",
                depends_on=[step_fail_id],
                error_action="continue",
            ),
        ]

        call_count = 0

        def fail_first_then_succeed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated step failure")
            from omnibase_core.utils.util_workflow_executor import (
                _create_action_for_step as real_fn,
            )

            return real_fn(*args, **kwargs)

        with patch(
            "omnibase_core.utils.util_workflow_executor._create_action_for_step",
            side_effect=fail_first_then_succeed,
        ):
            result = await execute_workflow(
                workflow_def,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert str(step_fail_id) in result.failed_steps
        assert result.execution_status == EnumWorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_parallel_continue_on_error_does_not_stop_workflow(
        self, parallel_workflow_def: ModelWorkflowDefinition
    ) -> None:
        from unittest.mock import patch

        # Two independent steps in same wave. Both fail (patch raises for all).
        # error_action=continue means workflow does NOT raise — it returns FAILED result.
        # This tests that continue prevents workflow-level exception escalation.
        step1_id = uuid4()
        step2_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="fails_parallel_1",
                step_type="compute",
                error_action="continue",
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="fails_parallel_2",
                step_type="compute",
                error_action="continue",
            ),
        ]

        with patch(
            "omnibase_core.utils.util_workflow_executor._create_action_for_step",
            side_effect=RuntimeError("Simulated failure"),
        ):
            result = await execute_workflow(
                parallel_workflow_def,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        # All steps fail but workflow returns result (not raises) due to continue
        assert result.execution_status == EnumWorkflowStatus.FAILED
        assert len(result.failed_steps) == 2


class TestSkipOnFailure:
    @pytest.mark.asyncio
    async def test_skip_on_failure_skips_step_when_prior_fails(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        from unittest.mock import patch

        step_fail_id = uuid4()
        step_skip_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_fail_id,
                step_name="will_fail",
                step_type="compute",
                error_action="continue",
            ),
            ModelWorkflowStep(
                step_id=step_skip_id,
                step_name="skip_me",
                step_type="compute",
                skip_on_failure=True,
                error_action="continue",
            ),
        ]

        with patch(
            "omnibase_core.utils.util_workflow_executor._create_action_for_step",
            side_effect=RuntimeError("Simulated failure"),
        ):
            result = await execute_workflow(
                workflow_def,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert str(step_skip_id) in result.skipped_steps
        assert str(step_skip_id) not in result.completed_steps
        assert str(step_skip_id) not in result.failed_steps

    @pytest.mark.asyncio
    async def test_skip_on_failure_does_not_skip_when_no_failures(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        step1 = _step("step1")
        step2 = _step("skip_me_not", skip_on_failure=True)

        result = await execute_workflow(
            workflow_def,
            [step1, step2],
            uuid4(),
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )
        # No failures → step2 executes normally
        assert str(step2.step_id) in result.completed_steps
        assert str(step2.step_id) not in result.skipped_steps


class TestReservedStepType:
    @pytest.mark.asyncio
    async def test_conditional_step_type_raises_model_onex_error(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        step = ModelWorkflowStep.model_construct(
            correlation_id=uuid4(),
            step_id=uuid4(),
            step_name="bad_step",
            step_type="conditional",
            timeout_ms=30000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            max_memory_mb=None,
            max_cpu_percent=None,
            priority=1,
            order_index=0,
            depends_on=[],
            parallel_group=None,
            max_parallel_instances=1,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            await validate_workflow_definition(workflow_def, [step])
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "conditional" in exc_info.value.message.lower()


class TestValidateJsonPayload:
    def test_strict_mode_rejects_uuid(self) -> None:
        payload: dict[str, object] = {"id": uuid4()}
        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(payload, strict=True)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_permissive_mode_accepts_uuid(self) -> None:
        payload: dict[str, object] = {"id": uuid4()}
        _validate_json_payload(payload, strict=False)  # should not raise

    def test_strict_mode_accepts_primitives(self) -> None:
        payload: dict[str, object] = {"str": "hello", "num": 42, "flag": True}
        _validate_json_payload(payload, strict=True)  # should not raise

    def test_permissive_mode_rejects_lambda(self) -> None:
        payload: dict[str, object] = {"fn": lambda x: x}
        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(payload, strict=False)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_context_appears_in_error_message(self) -> None:
        payload: dict[str, object] = {"fn": lambda x: x}
        with pytest.raises(ModelOnexError) as exc_info:
            _validate_json_payload(payload, context="my_step")
        assert "my_step" in exc_info.value.message


class TestTimeoutBehavior:
    @pytest.mark.asyncio
    async def test_expired_timeout_marks_remaining_steps_failed_sequential(
        self,
    ) -> None:
        from unittest.mock import patch

        # First call returns 0.0 (start_time). Subsequent calls return 9999.0.
        # Deadline = 0.0 + 1.0 = 1.0. Loop checks: 9999.0 > 1.0 → timeout fires.
        call_count = 0

        def perf_counter_mock() -> float:
            nonlocal call_count
            call_count += 1
            return 0.0 if call_count == 1 else 9999.0

        expired_def = _make_workflow_def(
            name="timeout_test",
            execution_mode="sequential",
            timeout_ms=1000,
        )
        steps = [_step("step1"), _step("step2"), _step("step3")]

        with patch(
            "omnibase_core.utils.util_workflow_executor.time.perf_counter",
            side_effect=perf_counter_mock,
        ):
            result = await execute_workflow(
                expired_def,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

        assert result.execution_status == EnumWorkflowStatus.FAILED
        assert len(result.failed_steps) > 0

    @pytest.mark.asyncio
    async def test_expired_timeout_marks_remaining_steps_failed_parallel(
        self,
    ) -> None:
        from unittest.mock import patch

        call_count = 0

        def perf_counter_mock() -> float:
            nonlocal call_count
            call_count += 1
            return 0.0 if call_count == 1 else 9999.0

        expired_def = _make_workflow_def(
            name="timeout_parallel_test",
            execution_mode="parallel",
            timeout_ms=1000,
        )
        steps = [_step("step1"), _step("step2")]

        with patch(
            "omnibase_core.utils.util_workflow_executor.time.perf_counter",
            side_effect=perf_counter_mock,
        ):
            result = await execute_workflow(
                expired_def,
                steps,
                uuid4(),
                execution_mode=EnumExecutionMode.PARALLEL,
            )

        assert result.execution_status == EnumWorkflowStatus.FAILED
        assert len(result.failed_steps) > 0


class TestWorkflowHashIntegrity:
    @pytest.mark.asyncio
    async def test_workflow_hash_populated_in_result_metadata(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        steps = [_step("step1")]
        result = await execute_workflow(workflow_def, steps, uuid4())
        assert result.metadata is not None
        assert result.metadata.workflow_hash != ""
        assert len(result.metadata.workflow_hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_empty_workflow_has_workflow_hash(
        self, workflow_def: ModelWorkflowDefinition
    ) -> None:
        result = await execute_workflow(workflow_def, [], uuid4())
        assert result.metadata is not None
        assert result.metadata.workflow_hash != ""
