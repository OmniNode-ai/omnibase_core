# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPhaseExitCondition and ModelSessionPhaseSpec.exit_conditions (OMN-11226)."""

from __future__ import annotations

import pytest

from omnibase_core.models.overseer.model_phase_exit_condition import (
    ModelPhaseExitCondition,
)
from omnibase_core.models.overseer.model_session_phase_spec import ModelSessionPhaseSpec


@pytest.mark.unit
def test_phase_exit_condition_pr_state() -> None:
    cond = ModelPhaseExitCondition(
        condition_type="pr_state",
        repo="OmniNode-ai/omnimarket",
        pr_number=686,
        required_state="merged",
    )
    assert cond.condition_type == "pr_state"
    assert cond.repo == "OmniNode-ai/omnimarket"
    assert cond.pr_number == 686
    assert cond.required_state == "merged"


@pytest.mark.unit
def test_phase_exit_condition_worker_count() -> None:
    cond = ModelPhaseExitCondition(
        condition_type="worker_count",
        operator="eq",
        value=0,
    )
    assert cond.condition_type == "worker_count"
    assert cond.operator == "eq"
    assert cond.value == 0


@pytest.mark.unit
def test_phase_exit_condition_custom_probe() -> None:
    cond = ModelPhaseExitCondition(
        condition_type="custom_probe",
        command="curl -fsS http://192.168.86.201:18085/health",  # onex-allow-internal-ip
        expected_exit_code=0,
    )
    assert cond.condition_type == "custom_probe"
    assert cond.expected_exit_code == 0


@pytest.mark.unit
def test_phase_exit_condition_task_complete() -> None:
    cond = ModelPhaseExitCondition(
        condition_type="task_complete",
        task_name="merge-sweep",
    )
    assert cond.condition_type == "task_complete"
    assert cond.task_name == "merge-sweep"


@pytest.mark.unit
def test_phase_exit_condition_time_elapsed() -> None:
    cond = ModelPhaseExitCondition(
        condition_type="time_elapsed",
        value=120,
    )
    assert cond.condition_type == "time_elapsed"
    assert cond.value == 120


@pytest.mark.unit
def test_phase_spec_has_exit_conditions() -> None:
    spec = ModelSessionPhaseSpec(
        phase_name="merge",
        exit_conditions=(
            ModelPhaseExitCondition(
                condition_type="worker_count", operator="eq", value=0
            ),
        ),
    )
    assert len(spec.exit_conditions) == 1
    assert spec.exit_conditions[0].condition_type == "worker_count"


@pytest.mark.unit
def test_phase_spec_exit_conditions_default_empty() -> None:
    spec = ModelSessionPhaseSpec(phase_name="warmup")
    assert spec.exit_conditions == ()


@pytest.mark.unit
def test_phase_exit_condition_is_frozen() -> None:
    cond = ModelPhaseExitCondition(condition_type="task_complete", task_name="abc")
    with pytest.raises(Exception):
        cond.task_name = "other"  # type: ignore[misc]


@pytest.mark.unit
def test_phase_exit_condition_rejects_extra_fields() -> None:
    with pytest.raises(Exception):
        ModelPhaseExitCondition(condition_type="task_complete", unknown_field="x")  # type: ignore[call-arg]
