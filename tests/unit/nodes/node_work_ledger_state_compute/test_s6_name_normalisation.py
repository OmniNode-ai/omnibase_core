# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""S6: ledger queries resolve canonical surface and lane names."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import ModelHoldScope, ModelRecipients
from omnibase_core.models.nodes.work_ledger_state import ModelWorkLedgerFoldInput
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    inbox,
    surface_lease,
)

from .work_ledger_events import eid, epoch, hold, line, message

pytestmark = pytest.mark.unit


def test_s6_inbox_query_normalises_lane_name() -> None:
    sent = message(eid(1), ModelRecipients(lanes=frozenset({"Lane-A"})))
    state = NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=(line(epoch()), line(sent)))
    )

    assert state.decidable
    for lane in ("lane-a", "LANE-A"):
        verdict = inbox(state, lane)
        assert verdict.status is EnumWorkLedgerVerdictStatus.FOUND
        assert [item.event_id for item in verdict.messages] == [sent.event_id]


def test_s6_surface_lease_query_normalises_surface_name() -> None:
    placed = hold(
        eid(2),
        ModelHoldScope(surfaces=frozenset({"201-Dev-Runtime"})),
        blocks=frozenset({EnumHoldBlock.DEPLOY}),
    )
    state = NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=(line(epoch()), line(placed)))
    )

    assert state.decidable
    for surface in ("201-dev-runtime", "201-DEV-RUNTIME"):
        verdict = surface_lease(state, surface)
        assert verdict.status is EnumWorkLedgerVerdictStatus.HELD
        assert [item.hold.event_id for item in verdict.holds] == [placed.event_id]
