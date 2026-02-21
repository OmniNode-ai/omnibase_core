# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for DecisionRecord and DecisionScore Pydantic models.

Covers:
- R1: DecisionRecord model is frozen and immutable
- R2: All fields have explicit types — no implicit defaults
- R3: Model exported from omnibase_core.contracts
- V3: Frozen model rejects mutation (raises TypeError on attribute assignment)

Test Categories:
1. Immutability / Frozen Model Tests
2. Field Type and Default Tests
3. Construction and Validation Tests
4. Export Path Tests
5. Edge Cases
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.contracts import DecisionRecord, DecisionScore
from omnibase_core.models.contracts.model_provenance_decision_record import (
    DecisionRecord as DecisionRecordDirect,
)
from omnibase_core.models.contracts.model_provenance_decision_record import (
    ModelProvenanceDecisionRecord,
)
from omnibase_core.models.contracts.model_provenance_decision_score import (
    DecisionScore as DecisionScoreDirect,
)
from omnibase_core.models.contracts.model_provenance_decision_score import (
    ModelProvenanceDecisionScore,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FIXED_TS = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
DECISION_UUID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _make_score(**kwargs: object) -> DecisionScore:
    """Return a valid DecisionScore, merging any overrides."""
    defaults: dict[str, object] = {
        "candidate": "model-a",
        "score": 0.92,
        "breakdown": {"accuracy": 0.95, "latency": 0.89},
    }
    defaults.update(kwargs)
    return DecisionScore(**defaults)  # type: ignore[arg-type]


def _make_record(**kwargs: object) -> DecisionRecord:
    """Return a valid DecisionRecord, merging any overrides."""
    defaults: dict[str, object] = {
        "decision_id": DECISION_UUID,
        "decision_type": "model_select",
        "timestamp": FIXED_TS,
        "candidates_considered": ["model-a", "model-b"],
        "constraints_applied": {"region": "us-east-1"},
        "scoring_breakdown": [_make_score()],
        "tie_breaker": None,
        "selected_candidate": "model-a",
        "agent_rationale": None,
        "reproducibility_snapshot": {"registry_version": "v2.1.0"},
    }
    defaults.update(kwargs)
    return DecisionRecord(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# R3: Export path tests
# ===========================================================================


@pytest.mark.unit
class TestDecisionRecordExports:
    """Verify R3: models are exported from omnibase_core.contracts."""

    def test_decision_record_importable_from_contracts(self) -> None:
        """DecisionRecord can be imported from omnibase_core.contracts."""
        assert DecisionRecord is DecisionRecordDirect

    def test_decision_score_importable_from_contracts(self) -> None:
        """DecisionScore can be imported from omnibase_core.contracts."""
        assert DecisionScore is DecisionScoreDirect

    def test_decision_record_is_alias_for_canonical_class(self) -> None:
        """DecisionRecord alias resolves to ModelProvenanceDecisionRecord."""
        assert DecisionRecord is ModelProvenanceDecisionRecord

    def test_decision_score_is_alias_for_canonical_class(self) -> None:
        """DecisionScore alias resolves to ModelProvenanceDecisionScore."""
        assert DecisionScore is ModelProvenanceDecisionScore

    def test_decision_record_in_contracts_all(self) -> None:
        """DecisionRecord appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "DecisionRecord" in contracts_module.__all__

    def test_decision_score_in_contracts_all(self) -> None:
        """DecisionScore appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "DecisionScore" in contracts_module.__all__


# ===========================================================================
# R1: Frozen / immutability tests
# ===========================================================================


@pytest.mark.unit
class TestDecisionRecordImmutability:
    """Verify R1: DecisionRecord and DecisionScore are frozen and immutable."""

    def test_decision_record_frozen_config(self) -> None:
        """model_config has frozen=True, extra='ignore', from_attributes=True."""
        cfg = DecisionRecord.model_config
        assert cfg.get("frozen") is True
        assert cfg.get("extra") == "ignore"
        assert cfg.get("from_attributes") is True

    def test_decision_score_frozen_config(self) -> None:
        """DecisionScore model_config has frozen=True."""
        cfg = DecisionScore.model_config
        assert cfg.get("frozen") is True
        assert cfg.get("extra") == "ignore"
        assert cfg.get("from_attributes") is True

    def test_decision_record_mutation_raises_type_error(self) -> None:
        """Attempting to mutate a DecisionRecord field raises TypeError (frozen model)."""
        record = _make_record()
        with pytest.raises((TypeError, ValidationError)):
            record.decision_id = UUID("00000000-0000-0000-0000-000000000001")  # type: ignore[misc]

    def test_decision_record_mutation_selected_candidate_raises(self) -> None:
        """Mutating selected_candidate on a frozen DecisionRecord raises TypeError."""
        record = _make_record()
        with pytest.raises((TypeError, ValidationError)):
            record.selected_candidate = "model-b"  # type: ignore[misc]

    def test_decision_score_mutation_raises_type_error(self) -> None:
        """Attempting to mutate a DecisionScore field raises TypeError."""
        score = _make_score()
        with pytest.raises((TypeError, ValidationError)):
            score.score = 0.5  # type: ignore[misc]

    def test_decision_record_from_attributes_orm_style(self) -> None:
        """from_attributes=True allows constructing from ORM-style objects."""

        class FakeORM:
            decision_id = DECISION_UUID
            decision_type = "workflow_route"
            timestamp = FIXED_TS
            candidates_considered = ["wf-a", "wf-b"]
            constraints_applied = {"env": "prod"}
            scoring_breakdown: list[DecisionScore] = []
            tie_breaker = None
            selected_candidate = "wf-a"
            agent_rationale = None
            reproducibility_snapshot = {"version": "1.0"}

        record = DecisionRecord.model_validate(FakeORM(), from_attributes=True)
        assert record.decision_id == DECISION_UUID
        assert record.selected_candidate == "wf-a"


# ===========================================================================
# R2: No implicit defaults on required fields
# ===========================================================================


@pytest.mark.unit
class TestDecisionRecordNoImplicitDefaults:
    """Verify R2: Required fields have no defaults — callers must inject them."""

    def test_timestamp_has_no_default(self) -> None:
        """timestamp field has no default — omitting it raises ValidationError."""
        with pytest.raises(ValidationError, match="timestamp"):
            DecisionRecord(
                decision_id=DECISION_UUID,
                decision_type="model_select",
                # timestamp intentionally omitted
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                selected_candidate="model-a",
                reproducibility_snapshot={},
            )

    def test_decision_id_has_no_default(self) -> None:
        """decision_id has no default — omitting it raises ValidationError."""
        with pytest.raises(ValidationError, match="decision_id"):
            DecisionRecord(
                # decision_id intentionally omitted
                decision_type="model_select",
                timestamp=FIXED_TS,
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                selected_candidate="model-a",
                reproducibility_snapshot={},
            )

    def test_decision_id_is_uuid_type(self) -> None:
        """decision_id field accepts UUID objects."""
        record = _make_record()
        assert isinstance(record.decision_id, UUID)
        assert record.decision_id == DECISION_UUID

    def test_decision_id_coerced_from_string(self) -> None:
        """Pydantic coerces UUID strings to UUID objects for decision_id."""
        record = _make_record(decision_id="550e8400-e29b-41d4-a716-446655440000")
        assert isinstance(record.decision_id, UUID)
        assert record.decision_id == DECISION_UUID

    def test_agent_rationale_defaults_to_none(self) -> None:
        """agent_rationale explicitly defaults to None (optional field)."""
        record = _make_record(agent_rationale=None)
        assert record.agent_rationale is None

    def test_agent_rationale_can_be_set(self) -> None:
        """agent_rationale can be provided as a string."""
        record = _make_record(agent_rationale="Selected for speed.")
        assert record.agent_rationale == "Selected for speed."

    def test_tie_breaker_defaults_to_none(self) -> None:
        """tie_breaker explicitly defaults to None."""
        record = _make_record()
        assert record.tie_breaker is None

    def test_tie_breaker_can_be_set(self) -> None:
        """tie_breaker can be provided as a string."""
        record = _make_record(tie_breaker="random_seed_42")
        assert record.tie_breaker == "random_seed_42"

    def test_required_fields_all_mandatory(self) -> None:
        """All non-optional fields are required — empty construction fails."""
        with pytest.raises(ValidationError):
            DecisionRecord()  # type: ignore[call-arg]


# ===========================================================================
# Construction and field validation tests
# ===========================================================================


@pytest.mark.unit
class TestDecisionRecordConstruction:
    """Test valid construction and field content of DecisionRecord."""

    def test_minimal_valid_construction(self) -> None:
        """A DecisionRecord with all required fields constructs correctly."""
        record = _make_record()
        assert record.decision_id == DECISION_UUID
        assert record.decision_type == "model_select"
        assert record.timestamp == FIXED_TS
        assert record.candidates_considered == ["model-a", "model-b"]
        assert record.constraints_applied == {"region": "us-east-1"}
        assert len(record.scoring_breakdown) == 1
        assert record.tie_breaker is None
        assert record.selected_candidate == "model-a"
        assert record.agent_rationale is None
        assert record.reproducibility_snapshot == {"registry_version": "v2.1.0"}

    def test_empty_lists_and_dicts_are_valid(self) -> None:
        """DecisionRecord allows empty collections for optional-style list fields."""
        record = _make_record(
            candidates_considered=[],
            constraints_applied={},
            scoring_breakdown=[],
            reproducibility_snapshot={},
        )
        assert record.candidates_considered == []
        assert record.constraints_applied == {}
        assert record.scoring_breakdown == []
        assert record.reproducibility_snapshot == {}

    def test_multiple_scores_in_breakdown(self) -> None:
        """scoring_breakdown accepts multiple DecisionScore objects."""
        scores = [
            _make_score(candidate="model-a", score=0.92),
            _make_score(candidate="model-b", score=0.81),
            _make_score(candidate="model-c", score=0.77),
        ]
        record = _make_record(scoring_breakdown=scores)
        assert len(record.scoring_breakdown) == 3
        assert record.scoring_breakdown[0].candidate == "model-a"
        assert record.scoring_breakdown[2].candidate == "model-c"

    def test_decision_types_variety(self) -> None:
        """decision_type accepts any non-empty string classifier."""
        for dt in ("model_select", "workflow_route", "tool_pick", "custom_decision"):
            record = _make_record(decision_type=dt)
            assert record.decision_type == dt

    def test_extra_fields_ignored(self) -> None:
        """extra='ignore' means unknown fields are silently dropped."""
        record = DecisionRecord(
            decision_id=DECISION_UUID,
            decision_type="model_select",
            timestamp=FIXED_TS,
            candidates_considered=[],
            constraints_applied={},
            scoring_breakdown=[],
            selected_candidate="model-a",
            reproducibility_snapshot={},
            unknown_future_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(record, "unknown_future_field")

    def test_constraints_applied_multiple_entries(self) -> None:
        """constraints_applied holds multiple string key-value pairs."""
        constraints = {
            "region": "us-east-1",
            "tier": "production",
            "feature_flag": "enabled",
        }
        record = _make_record(constraints_applied=constraints)
        assert record.constraints_applied == constraints

    def test_reproducibility_snapshot_multiple_entries(self) -> None:
        """reproducibility_snapshot holds multiple string key-value pairs."""
        snapshot = {
            "registry_version": "v2.1.0",
            "feature_flag_hash": "abc123",
            "model_registry_revision": "r42",
        }
        record = _make_record(reproducibility_snapshot=snapshot)
        assert record.reproducibility_snapshot == snapshot


@pytest.mark.unit
class TestDecisionScoreConstruction:
    """Test valid construction and field content of DecisionScore."""

    def test_minimal_valid_construction(self) -> None:
        """A DecisionScore with all required fields constructs correctly."""
        score = _make_score()
        assert score.candidate == "model-a"
        assert score.score == pytest.approx(0.92)
        assert score.breakdown == {"accuracy": 0.95, "latency": 0.89}

    def test_empty_breakdown_is_valid(self) -> None:
        """breakdown can be an empty dict."""
        score = _make_score(breakdown={})
        assert score.breakdown == {}

    def test_negative_score_is_accepted(self) -> None:
        """score field has no range constraint — negative values are accepted."""
        score = _make_score(score=-1.0)
        assert score.score == pytest.approx(-1.0)

    def test_score_above_one_is_accepted(self) -> None:
        """score field has no upper bound constraint."""
        score = _make_score(score=1.5)
        assert score.score == pytest.approx(1.5)

    def test_extra_fields_on_score_ignored(self) -> None:
        """extra='ignore' on DecisionScore drops unknown fields."""
        score = DecisionScore(
            candidate="model-x",
            score=0.5,
            breakdown={},
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(score, "unknown_field")

    def test_candidate_required(self) -> None:
        """Omitting candidate from DecisionScore raises ValidationError."""
        with pytest.raises(ValidationError, match="candidate"):
            DecisionScore(score=0.5, breakdown={})  # type: ignore[call-arg]

    def test_score_required(self) -> None:
        """Omitting score from DecisionScore raises ValidationError."""
        with pytest.raises(ValidationError, match="score"):
            DecisionScore(candidate="model-a", breakdown={})  # type: ignore[call-arg]

    def test_breakdown_required(self) -> None:
        """Omitting breakdown from DecisionScore raises ValidationError."""
        with pytest.raises(ValidationError, match="breakdown"):
            DecisionScore(candidate="model-a", score=0.5)  # type: ignore[call-arg]


# ===========================================================================
# Edge cases
# ===========================================================================


@pytest.mark.unit
class TestDecisionRecordEdgeCases:
    """Edge case tests for DecisionRecord."""

    def test_timestamp_with_timezone_preserved(self) -> None:
        """Timezone-aware datetime is preserved on the timestamp field."""
        record = _make_record(timestamp=FIXED_TS)
        assert record.timestamp.tzinfo is not None

    def test_decision_id_unique_uuids(self) -> None:
        """Two records with different UUIDs are not equal on decision_id."""
        r1 = _make_record(decision_id=UUID("550e8400-e29b-41d4-a716-446655440000"))
        r2 = _make_record(decision_id=UUID("550e8400-e29b-41d4-a716-446655440001"))
        assert r1.decision_id != r2.decision_id

    def test_selected_candidate_not_in_considered_list(self) -> None:
        """No constraint requiring selected_candidate to be in candidates_considered."""
        record = _make_record(
            candidates_considered=["model-a"],
            selected_candidate="model-z",  # not in the list
        )
        assert record.selected_candidate == "model-z"

    def test_scoring_breakdown_with_multi_dim_breakdown(self) -> None:
        """breakdown dict supports many dimensions."""
        many_dims = {f"dim_{i}": float(i) / 10 for i in range(20)}
        score = _make_score(breakdown=many_dims)
        assert len(score.breakdown) == 20

    def test_record_equality_same_data(self) -> None:
        """Two DecisionRecords with the same data compare equal."""
        r1 = _make_record()
        r2 = _make_record()
        assert r1 == r2

    def test_record_inequality_different_data(self) -> None:
        """Two DecisionRecords with different data are not equal."""
        r1 = _make_record(selected_candidate="model-a")
        r2 = _make_record(selected_candidate="model-b")
        assert r1 != r2

    def test_record_not_hashable_due_to_unhashable_fields(self) -> None:
        """Frozen DecisionRecord with list/dict fields is not hashable.

        Pydantic frozen models generate __hash__ from __dict__, but list and
        dict values are themselves not hashable, so hash() raises TypeError.
        This is expected — equality comparison still works fine.
        """
        r1 = _make_record()
        with pytest.raises(TypeError, match="unhashable type"):
            hash(r1)

    def test_score_not_hashable_due_to_unhashable_fields(self) -> None:
        """Frozen DecisionScore with dict fields is not hashable.

        DecisionScore.breakdown is a dict, which is unhashable, so the
        auto-generated Pydantic __hash__ raises TypeError. Equality works.
        """
        s1 = _make_score()
        with pytest.raises(TypeError, match="unhashable type"):
            hash(s1)
