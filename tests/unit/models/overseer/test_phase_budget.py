# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for phase budget and parallel dispatch fields (OMN-11227)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.models.overseer.model_session_contract import ModelSessionContract
from omnibase_core.models.overseer.model_session_phase_spec import ModelSessionPhaseSpec


@pytest.mark.unit
def test_phase_has_budget_fields() -> None:
    spec = ModelSessionPhaseSpec(
        phase_name="fix_prs",
        max_duration_minutes=120,
        budget_warning_pct=80,
        parallel_with=("integration",),
    )
    assert spec.max_duration_minutes == 120
    assert spec.budget_warning_pct == 80
    assert spec.parallel_with == ("integration",)


@pytest.mark.unit
def test_phase_budget_defaults() -> None:
    spec = ModelSessionPhaseSpec(phase_name="merge")
    assert spec.max_duration_minutes is None
    assert spec.budget_warning_pct == 80
    assert spec.parallel_with == ()


@pytest.mark.unit
def test_phase_max_duration_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ModelSessionPhaseSpec(phase_name="merge", max_duration_minutes=0)


@pytest.mark.unit
def test_phase_budget_warning_pct_range() -> None:
    with pytest.raises(ValueError):
        ModelSessionPhaseSpec(phase_name="merge", budget_warning_pct=101)
    with pytest.raises(ValueError):
        ModelSessionPhaseSpec(phase_name="merge", budget_warning_pct=0)


@pytest.mark.unit
def test_phase_parallel_with_multiple() -> None:
    spec = ModelSessionPhaseSpec(
        phase_name="fix_prs",
        parallel_with=("integration", "merge_sweep"),
    )
    assert spec.parallel_with == ("integration", "merge_sweep")


@pytest.mark.unit
def test_contract_has_max_parallel_workers() -> None:
    contract = ModelSessionContract(
        session_id="test",
        created_at=datetime.now(UTC),
        max_parallel_workers=5,
        phases=(ModelSessionPhaseSpec(phase_name="merge"),),
    )
    assert contract.max_parallel_workers == 5


@pytest.mark.unit
def test_contract_max_parallel_workers_default() -> None:
    contract = ModelSessionContract(
        session_id="test",
        created_at=datetime.now(UTC),
        phases=(ModelSessionPhaseSpec(phase_name="merge"),),
    )
    assert contract.max_parallel_workers == 7


@pytest.mark.unit
def test_contract_has_max_daily_cost() -> None:
    contract = ModelSessionContract(
        session_id="test",
        created_at=datetime.now(UTC),
        max_daily_cost_usd=50.0,
        phases=(ModelSessionPhaseSpec(phase_name="merge"),),
    )
    assert contract.max_daily_cost_usd == pytest.approx(50.0)


@pytest.mark.unit
def test_contract_max_daily_cost_default_none() -> None:
    contract = ModelSessionContract(
        session_id="test",
        created_at=datetime.now(UTC),
        phases=(ModelSessionPhaseSpec(phase_name="merge"),),
    )
    assert contract.max_daily_cost_usd is None
