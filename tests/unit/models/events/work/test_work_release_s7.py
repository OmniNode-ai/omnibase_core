# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""S7 of the second review of the typed ledger design (OMN-16177, plan task M4).

The review claimed that the fold does not check ``surface_restored`` and that a
surface release without it is valid. It is not reproducible: the pairing is
enforced where the event is built, so no fold input can carry the case. These
tests pin that, at the model, at the wire line and at the fold, so the plan text
"the fold checks this" can be amended to name the model as the enforcing layer.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_invalid_release_reason import EnumInvalidReleaseReason
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelWorkHoldReleased,
)
from omnibase_core.models.events.work.model_work_ledger_line import (
    parse_work_ledger_line,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import surface_lease
from tests.unit.nodes.node_work_ledger_state_compute.work_ledger_events import (
    T0,
    actor,
    eid,
    epoch,
    hold,
    line,
    release,
)

pytestmark = pytest.mark.unit

_LEASE_ID = eid(10)
_LEASE = hold(
    _LEASE_ID,
    ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
    expires_at=T0.replace(hour=13),
)


def _fold(*lines: str) -> ModelWorkLedgerState:
    return NodeWorkLedgerStateCompute().handle(ModelWorkLedgerFoldInput(lines=lines))


def _without_restored(release_line: str) -> str:
    payload: dict[str, Any] = json.loads(release_line)
    del payload["event"]["surface_restored"]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize(
    ("result", "restored"),
    [(EnumSurfaceResult.PASS, None), (None, True), (None, False)],
    ids=["result-only", "restored-true-only", "restored-false-only"],
)
def test_s7_model_refuses_half_a_surface_outcome(
    result: EnumSurfaceResult | None, restored: bool | None
) -> None:
    with pytest.raises(ValidationError, match="recorded together or not at all"):
        ModelWorkHoldReleased(
            event_id=eid(11),
            emitted_at=T0,
            actor=actor("lane-b"),
            summary="release",
            releases=_LEASE_ID,
            surface_result=result,
            surface_restored=restored,
        )


def test_s7_wire_line_without_restored_is_not_parsed() -> None:
    complete = line(release(eid(11), _LEASE_ID, surface_result=EnumSurfaceResult.PASS))
    assert parse_work_ledger_line(complete).event.event_id == eid(11)  # control

    with pytest.raises(ValueError, match="recorded together or not at all"):
        parse_work_ledger_line(_without_restored(complete))


def test_s7_fold_never_sees_a_release_with_result_and_no_restored() -> None:
    complete = line(release(eid(11), _LEASE_ID, surface_result=EnumSurfaceResult.PASS))
    healthy = _fold(line(epoch()), line(_LEASE), complete)
    assert healthy.decidable  # control: the same ledger with both fields is valid
    assert not healthy.invalid_releases
    assert (
        surface_lease(healthy, "dogfood-105").status
        is EnumWorkLedgerVerdictStatus.CLEAR
    )

    state = _fold(line(epoch()), line(_LEASE), _without_restored(complete))

    assert not state.decidable
    assert any("recorded together" in reason for reason in state.undecided_reasons)
    assert not state.invalid_releases
    assert [held.hold.event_id for held in state.holds_in_force] == [_LEASE_ID]


def test_s7_fold_refuses_a_surface_release_with_no_outcome() -> None:
    state = _fold(line(epoch()), line(_LEASE), line(release(eid(11), _LEASE_ID)))

    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.MISSING_SURFACE_RESULT
    ]
    assert [held.hold.event_id for held in state.holds_in_force] == [_LEASE_ID]
