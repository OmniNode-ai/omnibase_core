# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21818 -- a RuntimeLocal run joins no consumer group.

Every armed run built ``<handler>_run_<hex>`` and ``runtime_local_terminal_run_<hex>``
(and ``_t1``) groups: 3,800 Empty groups sat on the dev broker, a share of the
19,154 under which the broker segfaulted three times on 2026-10-31. A run now
reads its command and its terminals with no group, so a hundred runs leave at
most one group on a broker (they leave none).
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import cast

import pytest

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from tests.unit.runtime.test_runtime_local_terminal_isolation import (
    _bind,
    _build_runtime,
    _DurableBroker,
    _DurableBus,
)

pytestmark = pytest.mark.unit

RUNS = 100
#: Groups a hundred runs may leave on the broker in total.
MAX_GROUPS = 1


@pytest.mark.asyncio
async def test_groups_per_call_a_hundred_runs_leave_at_most_one_group(
    tmp_path: Path,
) -> None:
    broker = _DurableBroker()
    groups: set[str] = set()
    ungrouped_reads = 0
    for number in range(RUNS):
        runtime = _build_runtime(tmp_path / f"run{number}", correlation_id=uuid.uuid4())
        bus = _DurableBus(broker)
        _bind(runtime, bus)

        result = await runtime.run_async()

        assert result is EnumWorkflowResult.COMPLETED
        groups.update(bus.consumer_groups())
        ungrouped_reads += len(bus.subscriptions) - len(bus.consumer_groups())

    assert len(groups) <= MAX_GROUPS, sorted(groups)[:3]
    assert not any("_run_" in group for group in groups)
    # Each run read its command and at least its terminal, none of them in a group.
    assert ungrouped_reads >= 2 * RUNS


@pytest.mark.asyncio
async def test_groups_per_call_a_bus_without_the_ungrouped_read_keeps_run_scoped_ids(
    tmp_path: Path,
) -> None:
    """A bus with no broker cannot leak a group, so it keeps the run-scoped id (isolation unchanged)."""
    broker = _DurableBroker()
    runtime = _build_runtime(tmp_path / "run", correlation_id=uuid.uuid4())

    inner = _DurableBus(broker)

    class _GroupedOnlyBus:
        """The same broker double, hiding its group-less read."""

        start = inner.start
        close = inner.close
        publish = inner.publish
        subscribe = inner.subscribe

    _bind(runtime, cast("_DurableBus", _GroupedOnlyBus()))

    await runtime.run_async()

    assert inner.consumer_groups(), (
        "a grouped-only bus must still get run-scoped groups"
    )
    assert all(runtime.run_id.hex[:12] in g for g in inner.consumer_groups())
