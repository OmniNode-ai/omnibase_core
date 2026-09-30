# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ticket partition compatibility for legacy work-event payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import TypeAdapter

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkGoalRevised,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem

pytestmark = pytest.mark.unit

_TICKET_ID = "OMN-16177"
_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
_ACTOR = ModelSessionActor(session_handle="legacy-partition-test", agent_kind="unit")


def _legacy_events() -> tuple[ModelWorkClaimRequested, ModelWorkGoalRevised]:
    claim = ModelWorkClaimRequested(
        event_id=UUID("11111111-1111-4111-8111-111111111111"),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id=_TICKET_ID,
        summary="legacy ticket claim",
    )
    revision = ModelWorkGoalRevised(
        event_id=UUID("22222222-2222-4222-8222-222222222222"),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id=_TICKET_ID,
        summary="legacy ticket goal revision",
        goal_id=claim.event_id,
        dod_evidence=(
            ModelContractDodItem(
                id="contract-check",
                description="The existing ticket partition remains stable.",
                binds_ac=("AC1",),
            ),
        ),
        contract_schema_version="1.0.0",
        reason="Keep the existing ticketed work stream intact.",
        replaces=claim.event_id,
    )
    return claim, revision


@pytest.mark.parametrize(
    ("event_kind", "event_index"),
    [
        (EnumWorkEventKind.CLAIM_REQUESTED, 0),
        (EnumWorkEventKind.GOAL_REVISED, 1),
    ],
)
def test_legacy_ticket_partition_value_survives_event_round_trip(
    event_kind: EnumWorkEventKind,
    event_index: int,
) -> None:
    event = _legacy_events()[event_index]
    assert event.kind is event_kind

    partition_field = WORK_EVENT_PARTITION_KEY_FIELDS[event_kind]
    partition_value = getattr(event, partition_field)
    assert partition_value == _TICKET_ID

    restored = TypeAdapter(ModelWorkEvent).validate_json(event.model_dump_json())
    assert restored == event
    assert restored.ticket_id == _TICKET_ID
    assert getattr(restored, partition_field) == _TICKET_ID
    assert restored.model_dump(mode="json")["ticket_id"] == _TICKET_ID
