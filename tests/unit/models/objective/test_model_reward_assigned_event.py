# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for canonical ModelRewardAssignedEvent (OMN-2928).

Validates:
- Canonical shape: run-level score fields + policy signal fields
- UUID types for all identifiers
- reward_delta bounded to [-1.0, +1.0]
- score fields bounded to [0.0, 1.0]
- Round-trip JSON serialization/deserialization
- Import from objective subpackage __init__
- extra="forbid" — no unknown fields accepted
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_policy_type import EnumPolicyType
from omnibase_core.models.objective import ModelRewardAssignedEvent

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCORE_FIELDS = (
    "correctness",
    "safety",
    "cost",
    "latency",
    "maintainability",
    "human_time",
)


def _make_event(**overrides: object) -> ModelRewardAssignedEvent:
    """Build a valid ModelRewardAssignedEvent with sensible defaults."""
    run_id = uuid4()
    policy_id = uuid4()
    objective_id = uuid4()
    defaults: dict[str, object] = {
        "run_id": run_id,
        "correctness": 0.9,
        "safety": 0.85,
        "cost": 0.7,
        "latency": 0.8,
        "maintainability": 0.75,
        "human_time": 0.95,
        "evidence_refs": (uuid4(), uuid4()),
        "policy_id": policy_id,
        "policy_type": EnumPolicyType.TOOL_RELIABILITY,
        "reward_delta": 0.3,
        "objective_id": objective_id,
        "idempotency_key": "abc123",
        "occurred_at_utc": datetime.now(UTC).isoformat(),
    }
    defaults.update(overrides)
    return ModelRewardAssignedEvent(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestModelRewardAssignedEventConstruction:
    """ModelRewardAssignedEvent can be constructed with valid data."""

    def test_valid_construction(self) -> None:
        event = _make_event()
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.run_id, UUID)
        assert isinstance(event.policy_id, UUID)
        assert isinstance(event.objective_id, UUID)
        assert isinstance(event.policy_type, EnumPolicyType)
        assert isinstance(event.idempotency_key, str)
        assert isinstance(event.occurred_at_utc, str)
        assert isinstance(event.evidence_refs, tuple)

    def test_event_id_auto_generated(self) -> None:
        e1 = _make_event()
        e2 = _make_event()
        assert e1.event_id != e2.event_id

    def test_emitted_at_auto_generated(self) -> None:
        event = _make_event()
        assert isinstance(event.emitted_at, datetime)
        assert event.emitted_at.tzinfo is not None

    def test_evidence_refs_default_empty_tuple(self) -> None:
        """evidence_refs defaults to an empty tuple when not provided."""
        run_id = uuid4()
        policy_id = uuid4()
        objective_id = uuid4()
        event = ModelRewardAssignedEvent(
            run_id=run_id,
            correctness=1.0,
            safety=1.0,
            cost=1.0,
            latency=1.0,
            maintainability=1.0,
            human_time=1.0,
            policy_id=policy_id,
            policy_type=EnumPolicyType.PATTERN_EFFECTIVENESS,
            reward_delta=0.0,
            objective_id=objective_id,
            idempotency_key="key",
            occurred_at_utc="2026-02-27T00:00:00+00:00",
        )
        assert event.evidence_refs == ()

    def test_all_policy_types_accepted(self) -> None:
        for pt in EnumPolicyType:
            event = _make_event(policy_type=pt)
            assert event.policy_type == pt


# ---------------------------------------------------------------------------
# Score field bounds
# ---------------------------------------------------------------------------


class TestScoreFieldBounds:
    """Score fields are bounded to [0.0, 1.0]."""

    @pytest.mark.parametrize("field", _SCORE_FIELDS)
    def test_score_field_at_zero(self, field: str) -> None:
        event = _make_event(**{field: 0.0})
        assert getattr(event, field) == 0.0

    @pytest.mark.parametrize("field", _SCORE_FIELDS)
    def test_score_field_at_one(self, field: str) -> None:
        event = _make_event(**{field: 1.0})
        assert getattr(event, field) == 1.0

    @pytest.mark.parametrize("field", _SCORE_FIELDS)
    def test_score_field_below_zero_rejected(self, field: str) -> None:
        with pytest.raises(Exception):
            _make_event(**{field: -0.01})

    @pytest.mark.parametrize("field", _SCORE_FIELDS)
    def test_score_field_above_one_rejected(self, field: str) -> None:
        with pytest.raises(Exception):
            _make_event(**{field: 1.01})


# ---------------------------------------------------------------------------
# reward_delta bounds
# ---------------------------------------------------------------------------


class TestRewardDeltaBounds:
    """reward_delta is bounded to [-1.0, +1.0]."""

    def test_reward_delta_min(self) -> None:
        event = _make_event(reward_delta=-1.0)
        assert event.reward_delta == -1.0

    def test_reward_delta_max(self) -> None:
        event = _make_event(reward_delta=1.0)
        assert event.reward_delta == 1.0

    def test_reward_delta_zero(self) -> None:
        event = _make_event(reward_delta=0.0)
        assert event.reward_delta == 0.0

    def test_reward_delta_below_min_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_event(reward_delta=-1.01)

    def test_reward_delta_above_max_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_event(reward_delta=1.01)


# ---------------------------------------------------------------------------
# Round-trip serialization (the core of the gap fix)
# ---------------------------------------------------------------------------


class TestRoundTripSerialization:
    """Canonical event round-trips through JSON serialization/deserialization.

    This is the key DoD test: the producer serialises via model_dump_json()
    and the consumer deserialises via model_validate_json().
    """

    def test_model_dump_json_produces_valid_json(self) -> None:
        event = _make_event()
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_round_trip_model_validate_json(self) -> None:
        original = _make_event()
        json_str = original.model_dump_json()
        restored = ModelRewardAssignedEvent.model_validate_json(json_str)

        assert restored.event_id == original.event_id
        assert restored.run_id == original.run_id
        assert restored.policy_id == original.policy_id
        assert restored.objective_id == original.objective_id
        assert restored.policy_type == original.policy_type
        assert restored.reward_delta == original.reward_delta
        assert restored.idempotency_key == original.idempotency_key
        assert restored.occurred_at_utc == original.occurred_at_utc
        assert restored.correctness == original.correctness
        assert restored.safety == original.safety
        assert restored.cost == original.cost
        assert restored.latency == original.latency
        assert restored.maintainability == original.maintainability
        assert restored.human_time == original.human_time
        assert restored.evidence_refs == original.evidence_refs

    def test_round_trip_model_dump_dict(self) -> None:
        original = _make_event()
        data = original.model_dump()
        restored = ModelRewardAssignedEvent.model_validate(data)
        assert restored == original

    def test_uuid_fields_serialized_as_strings(self) -> None:
        """UUIDs serialise as strings in JSON (compatible with consumer str fields)."""
        event = _make_event()
        parsed = json.loads(event.model_dump_json())
        # UUIDs become strings in JSON
        UUID(parsed["event_id"])  # must parse as valid UUID string
        UUID(parsed["run_id"])
        UUID(parsed["policy_id"])
        UUID(parsed["objective_id"])

    def test_evidence_refs_serialized_as_list_of_strings(self) -> None:
        ref1, ref2 = uuid4(), uuid4()
        event = _make_event(evidence_refs=(ref1, ref2))
        parsed = json.loads(event.model_dump_json())
        assert isinstance(parsed["evidence_refs"], list)
        assert UUID(parsed["evidence_refs"][0]) == ref1
        assert UUID(parsed["evidence_refs"][1]) == ref2

    def test_score_vector_fields_preserved(self) -> None:
        event = _make_event(
            correctness=0.91,
            safety=0.82,
            cost=0.73,
            latency=0.84,
            maintainability=0.75,
            human_time=0.96,
        )
        restored = ModelRewardAssignedEvent.model_validate_json(event.model_dump_json())
        assert restored.correctness == pytest.approx(0.91)
        assert restored.safety == pytest.approx(0.82)
        assert restored.cost == pytest.approx(0.73)
        assert restored.latency == pytest.approx(0.84)
        assert restored.maintainability == pytest.approx(0.75)
        assert restored.human_time == pytest.approx(0.96)


# ---------------------------------------------------------------------------
# Strictness
# ---------------------------------------------------------------------------


class TestModelRewardAssignedEventStrictness:
    """extra='forbid' — unknown fields are rejected."""

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_event(unknown_field="should_fail")  # type: ignore[call-overload]

    def test_frozen_immutable(self) -> None:
        event = _make_event()
        with pytest.raises(Exception):
            event.reward_delta = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Import from subpackage
# ---------------------------------------------------------------------------


class TestImport:
    """ModelRewardAssignedEvent is importable from omnibase_core.models.objective."""

    def test_import_from_objective_init(self) -> None:
        from omnibase_core.models.objective import ModelRewardAssignedEvent as Imported

        assert Imported is ModelRewardAssignedEvent
