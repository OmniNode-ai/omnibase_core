# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hold kinds and their value types (OMN-16177, typed work ledger task T1).

Covers the three acceptance criteria of task T1:

- AC1: an empty ``ModelHoldScope``, ``all_repos=True`` with non-empty ``repos``,
  ``expires_at`` without surfaces, and an invalid ``reap=True`` release are each
  refused with ``ValidationError``.
- AC2: ``ModelPrKey`` normalises the repo, so two spellings of one PR compare
  and hash equal.
- AC3: ``WORK_EVENT_PARTITION_KEY_FIELDS`` covers every ``EnumWorkEventKind``
  member, including the two hold kinds.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkHoldPlaced,
    ModelWorkHoldReleased,
)

pytestmark = pytest.mark.unit

_EMITTED_AT = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)


def _actor() -> ModelSessionActor:
    return ModelSessionActor(
        session_handle="typed-ledger-t1",
        controller_id=uuid.UUID("e2583369-b006-4c23-9a79-b13061f0ea09"),
        agent_kind="build-lane",
    )


def _pr_scope() -> ModelHoldScope:
    return ModelHoldScope(
        prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4005)})
    )


def _surface_scope() -> ModelHoldScope:
    return ModelHoldScope(surfaces=frozenset({"dogfood-105"}))


def _placed(**overrides: object) -> ModelWorkHoldPlaced:
    kwargs: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "emitted_at": _EMITTED_AT,
        "actor": _actor(),
        "summary": "hold omnibase_infra#4005 until the lab pass",
        "scope": _pr_scope(),
        "blocks": frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
    }
    kwargs.update(overrides)
    return ModelWorkHoldPlaced(**kwargs)  # type: ignore[arg-type]


def _released(**overrides: object) -> ModelWorkHoldReleased:
    kwargs: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "emitted_at": _EMITTED_AT,
        "actor": _actor(),
        "summary": "lab pass read; hold lifted",
        "releases": uuid.uuid4(),
    }
    kwargs.update(overrides)
    return ModelWorkHoldReleased(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC1 — each invalid shape is refused
# ---------------------------------------------------------------------------


def _empty_scope() -> object:
    return ModelHoldScope()


def _all_repos_with_repos() -> object:
    return ModelHoldScope(all_repos=True, repos=frozenset({"omnibase_infra"}))


def _expires_without_surfaces() -> object:
    return _placed(expires_at=_EMITTED_AT + timedelta(hours=1))


def _reap_with_partial_scope() -> object:
    return _released(
        reap=True,
        partial_scope=_surface_scope(),
        surface_result=EnumSurfaceResult.ABORTED,
        surface_restored=True,
    )


def _reap_without_surface_outcome() -> object:
    return _released(reap=True)


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(_empty_scope, id="empty-scope"),
        pytest.param(_all_repos_with_repos, id="all-repos-with-repos"),
        pytest.param(_expires_without_surfaces, id="expires-at-without-surfaces"),
        pytest.param(_reap_with_partial_scope, id="reap-with-partial-scope"),
        pytest.param(_reap_without_surface_outcome, id="reap-without-surface-outcome"),
    ],
)
def test_invalid_hold_shapes_are_refused(build: object) -> None:
    assert callable(build)
    with pytest.raises(ValidationError):
        build()


def test_empty_blocks_is_refused() -> None:
    with pytest.raises(ValidationError):
        _placed(blocks=frozenset())


def test_surface_result_without_restored_is_refused() -> None:
    with pytest.raises(ValidationError):
        _released(surface_result=EnumSurfaceResult.PASS)


def test_restored_without_surface_result_is_refused() -> None:
    with pytest.raises(ValidationError):
        _released(surface_restored=True)


def test_blank_surface_or_lane_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelHoldScope(surfaces=frozenset({"  "}))
    with pytest.raises(ValidationError):
        ModelHoldScope(lanes=frozenset({""}))


def test_bad_repo_name_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelPrKey(repo="OmniNode-ai/omnibase_core", number=1)
    with pytest.raises(ValidationError):
        ModelHoldScope(repos=frozenset({"omnibase core"}))


def test_pr_number_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ModelPrKey(repo="omnibase_core", number=0)


def test_recipients_must_name_someone() -> None:
    with pytest.raises(ValidationError):
        ModelRecipients()


def test_valid_shapes_construct() -> None:
    """Positive control for AC1: each refused shape has a valid neighbour."""
    lease = _placed(
        scope=_surface_scope(),
        blocks=frozenset({EnumHoldBlock.DEPLOY}),
        expires_at=_EMITTED_AT + timedelta(hours=1),
        until_text="until the proof run ends",
        addressed_to=ModelRecipients(all_lanes=True),
        runtime_only=True,
    )
    assert lease.expires_at is not None
    assert ModelHoldScope(all_repos=True).all_repos is True
    reap = _released(
        releases=lease.event_id,
        reap=True,
        surface_result=EnumSurfaceResult.ABORTED,
        surface_restored=True,
    )
    assert reap.reap is True
    partial = _released(partial_scope=_pr_scope())
    assert partial.partial_scope is not None
    assert partial.reap is False


# ---------------------------------------------------------------------------
# AC2 — one PR, one key
# ---------------------------------------------------------------------------


def test_pr_key_normalises_repo_case() -> None:
    upper = ModelPrKey(repo="OmniBase_Infra", number=4005)
    lower = ModelPrKey(repo="omnibase_infra", number=4005)
    assert upper == lower
    assert hash(upper) == hash(lower)
    assert upper in {lower}
    assert len({upper, lower}) == 1
    assert upper.repo == "omnibase_infra"


def test_pr_key_distinguishes_number_and_repo() -> None:
    base = ModelPrKey(repo="omnibase_infra", number=4005)
    assert base != ModelPrKey(repo="omnibase_infra", number=4006)
    assert base != ModelPrKey(repo="omnimarket", number=4005)


def test_hold_scope_repos_are_normalised() -> None:
    scope = ModelHoldScope(repos=frozenset({"OmniMarket", "omnimarket"}))
    assert scope.repos == frozenset({"omnimarket"})


def test_hold_scope_is_hashable_and_serialises_sorted() -> None:
    """Set-valued fields dump in sorted order, so the JSON form is deterministic."""
    scope = ModelHoldScope(
        prs=frozenset(
            {
                ModelPrKey(repo="omnimarket", number=2),
                ModelPrKey(repo="omnibase_infra", number=10),
                ModelPrKey(repo="omnibase_infra", number=9),
            }
        ),
        repos=frozenset({"zeta", "alpha"}),
        lanes=frozenset({"lane-b", "lane-a"}),
    )
    assert hash(scope) == hash(ModelHoldScope.model_validate(scope.model_dump()))
    dumped = json.loads(scope.model_dump_json())
    assert dumped["prs"] == [
        {"repo": "omnibase_infra", "number": 9},
        {"repo": "omnibase_infra", "number": 10},
        {"repo": "omnimarket", "number": 2},
    ]
    assert dumped["repos"] == ["alpha", "zeta"]
    assert dumped["lanes"] == ["lane-a", "lane-b"]


def test_hold_placed_round_trips_through_json() -> None:
    placed = _placed(addressed_to=ModelRecipients(lanes=frozenset({"pr-land-1"})))
    again = ModelWorkHoldPlaced.model_validate_json(placed.model_dump_json())
    assert again == placed
    assert again.model_dump_json() == placed.model_dump_json()


def test_hold_released_round_trips_through_json() -> None:
    released = _released(
        partial_scope=_pr_scope(),
        surface_result=EnumSurfaceResult.PASS,
        surface_restored=True,
    )
    again = ModelWorkHoldReleased.model_validate_json(released.model_dump_json())
    assert again == released


# ---------------------------------------------------------------------------
# AC3 — every kind has a partition key; hold kinds are narrative
# ---------------------------------------------------------------------------


def test_every_kind_has_a_partition_key() -> None:
    assert set(WORK_EVENT_PARTITION_KEY_FIELDS) == set(EnumWorkEventKind)


def test_hold_kinds_exist_and_partition_on_actor_key() -> None:
    assert EnumWorkEventKind.HOLD_PLACED.value == "work.hold.placed"
    assert EnumWorkEventKind.HOLD_RELEASED.value == "work.hold.released"
    for kind in (EnumWorkEventKind.HOLD_PLACED, EnumWorkEventKind.HOLD_RELEASED):
        assert WORK_EVENT_PARTITION_KEY_FIELDS[kind] == "actor_key"


def test_hold_models_pin_their_kind() -> None:
    assert (
        ModelWorkHoldPlaced.model_fields["kind"].default
        is EnumWorkEventKind.HOLD_PLACED
    )
    assert (
        ModelWorkHoldReleased.model_fields["kind"].default
        is EnumWorkEventKind.HOLD_RELEASED
    )
    with pytest.raises(ValidationError):
        _placed(kind=EnumWorkEventKind.HOLD_RELEASED)


def test_hold_models_are_frozen_and_forbid_extra() -> None:
    placed = _placed()
    with pytest.raises(ValidationError):
        placed.runtime_only = True  # type: ignore[misc]
    with pytest.raises(ValidationError):
        _placed(consent="yes")
    with pytest.raises(ValidationError):
        ModelPrKey(repo="omnibase_core", number=1, state="open")  # type: ignore[call-arg]
