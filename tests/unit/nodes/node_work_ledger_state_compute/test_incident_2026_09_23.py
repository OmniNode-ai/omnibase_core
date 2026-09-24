# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The 2026-09-23 runtime-merge pause incident, replayed as typed events
(OMN-19405, typed work ledger plan T4, AC1).

Three ledger rows decided this incident:

- ``2026-09-23T14:27:35Z | STATUS | lane=omn17427-foreground`` paused runtime
  merges fleet-wide in prose ("RUNTIME MERGES STAY PAUSED ... Non-runtime
  merges continue").
- ``2026-09-23T21:57:13Z | STATUS | lane=merge-drain-7f`` declared a second
  runtime-merge pause for the 22:00Z-22:50Z window.
- ``2026-09-23T22:08:49Z | RELEASE | lane=merge-drain-7f`` lifted the window
  pause and said, in prose, that the 14:27:35Z pause "STILL STANDS".

The prose parser dropped the 14:27:35Z pause and put six runtime PRs on
WOULD-ARM. Re-expressed as typed events, the release names the window hold by
event_id and can release nothing else, so the fold keeps the 14:27:35Z hold in
force. The six runtime PRs are the ones the incident rows and the plan's
section 2 name; the drain map's own WOULD-ARM list was not recorded.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import ModelHoldScope, ModelPrKey
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import is_held

from .work_ledger_events import eid, epoch, hold, line, pr, release

pytestmark = pytest.mark.unit

_PAUSE_1427 = eid(142735)
_PAUSE_2157 = eid(215713)
_RELEASE_2208 = eid(220849)

_RUNTIME_PRS = (
    pr("omnibase_infra", 4013),
    pr("omnibase_infra", 4015),
    pr("omnibase_infra", 4002),
    pr("omnibase_infra", 4005),
    pr("omnimarket", 2821),
    pr("omnimarket", 2809),
)
_NON_RUNTIME_PRS = (pr("omnibase_infra", 4020), pr("omnimarket", 2830))


def _incident_lines() -> tuple[str, ...]:
    fleet_runtime_pause = ModelHoldScope(all_repos=True)
    return (
        line(epoch()),
        line(
            hold(
                _PAUSE_1427,
                fleet_runtime_pause,
                blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
                runtime_only=True,
                lane="omn17427-foreground",
                emitted_at=datetime(2026, 9, 23, 14, 27, 35, tzinfo=UTC),
                summary=(
                    "RUNTIME MERGES STAY PAUSED by the orchestrator until the "
                    "deploy-publish drain ends. Non-runtime merges continue."
                ),
            )
        ),
        line(
            hold(
                _PAUSE_2157,
                fleet_runtime_pause,
                blocks=frozenset({EnumHoldBlock.MERGE}),
                runtime_only=True,
                lane="merge-drain-7f",
                emitted_at=datetime(2026, 9, 23, 21, 57, 13, tzinfo=UTC),
                summary="RUNTIME MERGES PAUSED from 22:00Z to 22:50Z",
                until_text="Lifted by a RELEASE naming this row, or at 22:50Z.",
            )
        ),
        line(
            release(
                _RELEASE_2208,
                _PAUSE_2157,
                lane="merge-drain-7f",
                emitted_at=datetime(2026, 9, 23, 22, 8, 49, tzinfo=UTC),
                summary=(
                    "The 22:00Z-22:50Z runtime-merge window pause is lifted "
                    "early. The separate runtime-merge pause of "
                    "2026-09-23T14:27:35Z STILL STANDS."
                ),
            )
        ),
    )


def _state() -> ModelWorkLedgerState:
    return NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=_incident_lines())
    )


@pytest.mark.parametrize(
    "runtime_pr", _RUNTIME_PRS, ids=lambda p: f"{p.repo}#{p.number}"
)
@pytest.mark.parametrize("action", [EnumHoldBlock.MERGE, EnumHoldBlock.ARM])
def test_runtime_pr_is_held_by_the_1427_pause_only(
    runtime_pr: ModelPrKey, action: EnumHoldBlock
) -> None:
    verdict = is_held(_state(), runtime_pr, action, runtime_affecting=True)

    assert verdict.status is EnumWorkLedgerVerdictStatus.HELD
    assert verdict.exit_code == 3
    assert [held.hold.event_id for held in verdict.holds] == [_PAUSE_1427]


@pytest.mark.parametrize(
    "runtime_pr", _RUNTIME_PRS, ids=lambda p: f"{p.repo}#{p.number}"
)
def test_unknown_runtime_class_is_treated_as_runtime(runtime_pr: ModelPrKey) -> None:
    verdict = is_held(_state(), runtime_pr, EnumHoldBlock.MERGE, runtime_affecting=None)

    assert verdict.status is EnumWorkLedgerVerdictStatus.HELD


@pytest.mark.parametrize(
    "plain_pr", _NON_RUNTIME_PRS, ids=lambda p: f"{p.repo}#{p.number}"
)
def test_non_runtime_pr_in_the_same_repos_is_clear(plain_pr: ModelPrKey) -> None:
    verdict = is_held(_state(), plain_pr, EnumHoldBlock.MERGE, runtime_affecting=False)

    assert verdict.status is EnumWorkLedgerVerdictStatus.CLEAR
    assert verdict.exit_code == 0
    assert verdict.holds == ()


def test_the_window_pause_is_released_and_nothing_else() -> None:
    state = _state()

    assert [held.hold.event_id for held in state.holds_in_force] == [_PAUSE_1427]
    assert state.invalid_releases == ()
