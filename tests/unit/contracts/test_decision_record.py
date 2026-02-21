#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Decision Provenance models (OMN-2464).

Covers ModelProvenanceDecisionScore and ModelProvenanceDecisionRecord,
including:
    - Valid construction (minimal and full field sets)
    - R1: frozen=True immutability
    - R2: No implicit defaults for required fields
    - R3: Export paths from omnibase_core.contracts and omnibase_core.models.contracts
    - Nullable optional fields (tie_breaker, agent_rationale)
    - Field type validation
    - Public alias (DecisionRecord, DecisionScore) accessibility
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.contracts import DecisionRecord, DecisionScore
from omnibase_core.models.contracts.model_provenance_decision_record import (
    ModelProvenanceDecisionRecord,
)
from omnibase_core.models.contracts.model_provenance_decision_score import (
    ModelProvenanceDecisionScore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_TIMESTAMP = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
DECISION_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def make_score(
    candidate: str = "claude-3-opus",
    score: float = 0.87,
    breakdown: dict[str, float] | None = None,
) -> ModelProvenanceDecisionScore:
    if breakdown is None:
        breakdown = {"quality": 0.45, "speed": 0.25, "cost": 0.17}
    return ModelProvenanceDecisionScore(
        candidate=candidate,
        score=score,
        breakdown=breakdown,
    )


def make_record(**overrides: object) -> ModelProvenanceDecisionRecord:
    defaults: dict[str, object] = {
        "decision_id": DECISION_ID,
        "decision_type": "model_select",
        "timestamp": FIXED_TIMESTAMP,
        "candidates_considered": ["claude-3-opus", "gpt-4"],
        "constraints_applied": {"max_cost_usd": "0.05"},
        "scoring_breakdown": [make_score()],
        "tie_breaker": None,
        "selected_candidate": "claude-3-opus",
        "agent_rationale": None,
        "reproducibility_snapshot": {"routing_version": "1.2.3"},
    }
    defaults.update(overrides)
    return ModelProvenanceDecisionRecord(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# Tests: ModelProvenanceDecisionScore
# ===========================================================================


@pytest.mark.unit
class TestModelProvenanceDecisionScore:
    """Tests for ModelProvenanceDecisionScore."""

    # -----------------------------------------------------------------------
    # Valid construction
    # -----------------------------------------------------------------------

    def test_valid_construction_basic(self) -> None:
        """Construct a score with all fields."""
        score = ModelProvenanceDecisionScore(
            candidate="claude-3-opus",
            score=0.87,
            breakdown={"quality": 0.45, "speed": 0.25, "cost": 0.17},
        )
        assert score.candidate == "claude-3-opus"
        assert score.score == 0.87
        assert score.breakdown == {"quality": 0.45, "speed": 0.25, "cost": 0.17}

    def test_valid_construction_zero_score(self) -> None:
        """Score of zero is valid."""
        score = ModelProvenanceDecisionScore(
            candidate="gpt-4",
            score=0.0,
            breakdown={},
        )
        assert score.score == 0.0
        assert score.breakdown == {}

    def test_valid_construction_negative_score(self) -> None:
        """Negative scores are allowed (no range constraint)."""
        score = ModelProvenanceDecisionScore(
            candidate="llama-2",
            score=-1.5,
            breakdown={"penalty": -1.5},
        )
        assert score.score == -1.5

    def test_valid_construction_empty_breakdown(self) -> None:
        """Empty breakdown dict is valid."""
        score = ModelProvenanceDecisionScore(
            candidate="gpt-4",
            score=0.5,
            breakdown={},
        )
        assert score.breakdown == {}

    # -----------------------------------------------------------------------
    # R1: Immutability (frozen=True)
    # -----------------------------------------------------------------------

    def test_frozen_rejects_candidate_mutation(self) -> None:
        """Mutating candidate raises ValidationError (frozen=True)."""
        score = make_score()
        with pytest.raises(ValidationError):
            score.candidate = "gpt-4"

    def test_frozen_rejects_score_mutation(self) -> None:
        """Mutating score raises ValidationError (frozen=True)."""
        score = make_score()
        with pytest.raises(ValidationError):
            score.score = 0.5

    def test_frozen_rejects_breakdown_mutation(self) -> None:
        """Mutating breakdown raises ValidationError (frozen=True)."""
        score = make_score()
        with pytest.raises(ValidationError):
            score.breakdown = {}

    # -----------------------------------------------------------------------
    # R2: Required fields have no defaults
    # -----------------------------------------------------------------------

    def test_missing_candidate_raises(self) -> None:
        """Omitting candidate raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionScore(
                score=0.87,
                breakdown={"quality": 0.45},
            )  # type: ignore[call-arg]

    def test_missing_score_raises(self) -> None:
        """Omitting score raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionScore(
                candidate="claude-3-opus",
                breakdown={"quality": 0.45},
            )  # type: ignore[call-arg]

    def test_missing_breakdown_raises(self) -> None:
        """Omitting breakdown raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionScore(
                candidate="claude-3-opus",
                score=0.87,
            )  # type: ignore[call-arg]

    def test_empty_candidate_raises(self) -> None:
        """Empty string for candidate raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionScore(
                candidate="",
                score=0.87,
                breakdown={"quality": 0.45},
            )

    # -----------------------------------------------------------------------
    # Extra fields ignored (extra="ignore")
    # -----------------------------------------------------------------------

    def test_extra_fields_ignored(self) -> None:
        """Extra fields are ignored, not rejected."""
        score = ModelProvenanceDecisionScore(
            candidate="claude-3-opus",
            score=0.87,
            breakdown={},
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert score.candidate == "claude-3-opus"
        assert not hasattr(score, "unknown_field")

    # -----------------------------------------------------------------------
    # from_attributes=True
    # -----------------------------------------------------------------------

    def test_from_attributes(self) -> None:
        """Model can be constructed from ORM-like objects."""

        class FakeOrmScore:
            candidate = "gpt-4"
            score = 0.75
            breakdown = {"quality": 0.40, "cost": 0.35}

        score = ModelProvenanceDecisionScore.model_validate(
            FakeOrmScore(), from_attributes=True
        )
        assert score.candidate == "gpt-4"
        assert score.score == 0.75


# ===========================================================================
# Tests: ModelProvenanceDecisionRecord
# ===========================================================================


@pytest.mark.unit
class TestModelProvenanceDecisionRecord:
    """Tests for ModelProvenanceDecisionRecord."""

    # -----------------------------------------------------------------------
    # Valid construction
    # -----------------------------------------------------------------------

    def test_valid_construction_minimal(self) -> None:
        """Construct a record with only required fields (tie_breaker and
        agent_rationale default to None)."""
        record = ModelProvenanceDecisionRecord(
            decision_id=DECISION_ID,
            decision_type="model_select",
            timestamp=FIXED_TIMESTAMP,
            candidates_considered=["claude-3-opus"],
            constraints_applied={},
            scoring_breakdown=[],
            selected_candidate="claude-3-opus",
            reproducibility_snapshot={},
        )
        assert record.decision_id == DECISION_ID
        assert record.tie_breaker is None
        assert record.agent_rationale is None

    def test_valid_construction_full(self) -> None:
        """Construct a record with all fields populated."""
        score = make_score("route-a")
        record = ModelProvenanceDecisionRecord(
            decision_id=DECISION_ID,
            decision_type="workflow_route",
            timestamp=FIXED_TIMESTAMP,
            candidates_considered=["route-a", "route-b"],
            constraints_applied={"latency_ms": "500"},
            scoring_breakdown=[score],
            tie_breaker="alphabetical",
            selected_candidate="route-a",
            agent_rationale="Lowest latency route.",
            reproducibility_snapshot={"planner_version": "2.1.0"},
        )
        assert record.decision_type == "workflow_route"
        assert record.tie_breaker == "alphabetical"
        assert record.agent_rationale == "Lowest latency route."
        assert len(record.scoring_breakdown) == 1

    def test_empty_candidates_and_constraints(self) -> None:
        """Empty lists and dicts are valid field values when scoring_breakdown is also empty.

        make_record uses 'claude-3-opus' as the default selected_candidate; this
        test does not override that, so selected_candidate must be preserved as-is
        even though candidates_considered is empty (cross-validation is skipped
        when candidates_considered is empty).
        """
        record = make_record(
            candidates_considered=[],
            constraints_applied={},
            scoring_breakdown=[],
        )
        assert record.candidates_considered == []
        assert record.constraints_applied == {}
        assert record.selected_candidate == "claude-3-opus"

    def test_multiple_scoring_breakdown_entries(self) -> None:
        """Multiple score entries are valid when all candidates are in candidates_considered."""
        scores = [
            make_score("claude-3-opus", 0.9, {"q": 0.9}),
            make_score("gpt-4", 0.7, {"q": 0.7}),
        ]
        record = make_record(scoring_breakdown=scores)
        assert len(record.scoring_breakdown) == 2

    def test_various_decision_types(self) -> None:
        """Decision type is a free string — any value is valid."""
        for dt in ("model_select", "workflow_route", "tool_pick", "custom_type"):
            record = make_record(decision_type=dt)
            assert record.decision_type == dt

    # -----------------------------------------------------------------------
    # R1: Immutability (frozen=True)
    # -----------------------------------------------------------------------

    def test_frozen_rejects_decision_id_mutation(self) -> None:
        """Mutating decision_id raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.decision_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_frozen_rejects_decision_type_mutation(self) -> None:
        """Mutating decision_type raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.decision_type = "tool_pick"

    def test_frozen_rejects_timestamp_mutation(self) -> None:
        """Mutating timestamp raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.timestamp = datetime(2025, 1, 1, tzinfo=UTC)

    def test_frozen_rejects_candidates_mutation(self) -> None:
        """Mutating candidates_considered raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.candidates_considered = []

    def test_frozen_rejects_selected_candidate_mutation(self) -> None:
        """Mutating selected_candidate raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.selected_candidate = "gpt-4"

    def test_frozen_rejects_agent_rationale_mutation(self) -> None:
        """Mutating agent_rationale raises ValidationError."""
        record = make_record()
        with pytest.raises(ValidationError):
            record.agent_rationale = "new rationale"

    # -----------------------------------------------------------------------
    # R2: Required fields have no defaults (callers must inject)
    # -----------------------------------------------------------------------

    def test_missing_decision_id_raises(self) -> None:
        """Omitting decision_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionRecord(
                decision_type="model_select",
                timestamp=FIXED_TIMESTAMP,
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                selected_candidate="a",
                reproducibility_snapshot={},
            )  # type: ignore[call-arg]

    def test_missing_timestamp_raises(self) -> None:
        """Omitting timestamp raises ValidationError — no datetime.now() default."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionRecord(
                decision_id=DECISION_ID,
                decision_type="model_select",
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                selected_candidate="a",
                reproducibility_snapshot={},
            )  # type: ignore[call-arg]

    def test_missing_selected_candidate_raises(self) -> None:
        """Omitting selected_candidate raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionRecord(
                decision_id=DECISION_ID,
                decision_type="model_select",
                timestamp=FIXED_TIMESTAMP,
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                reproducibility_snapshot={},
            )  # type: ignore[call-arg]

    def test_missing_reproducibility_snapshot_raises(self) -> None:
        """Omitting reproducibility_snapshot raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelProvenanceDecisionRecord(
                decision_id=DECISION_ID,
                decision_type="model_select",
                timestamp=FIXED_TIMESTAMP,
                candidates_considered=[],
                constraints_applied={},
                scoring_breakdown=[],
                selected_candidate="a",
            )  # type: ignore[call-arg]

    def test_empty_decision_type_raises(self) -> None:
        """Empty string for decision_type raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            make_record(decision_type="")

    def test_empty_selected_candidate_raises(self) -> None:
        """Empty string for selected_candidate raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            make_record(selected_candidate="")

    def test_naive_timestamp_raises(self) -> None:
        """Timezone-naive datetime for timestamp raises ValidationError."""
        from datetime import datetime as dt

        with pytest.raises(ValidationError):
            make_record(timestamp=dt(2026, 1, 1))

    def test_agent_rationale_defaults_to_none(self) -> None:
        """agent_rationale has explicit None default — callers may omit it."""
        record = make_record()
        assert record.agent_rationale is None

    def test_tie_breaker_defaults_to_none(self) -> None:
        """tie_breaker has explicit None default — callers may omit it."""
        record = make_record()
        assert record.tie_breaker is None

    def test_agent_rationale_can_be_set(self) -> None:
        """agent_rationale can be provided explicitly."""
        record = make_record(agent_rationale="Chosen for cost efficiency.")
        assert record.agent_rationale == "Chosen for cost efficiency."

    def test_tie_breaker_can_be_set(self) -> None:
        """tie_breaker can be provided explicitly."""
        record = make_record(tie_breaker="random")
        assert record.tie_breaker == "random"

    # -----------------------------------------------------------------------
    # Extra fields ignored (extra="ignore")
    # -----------------------------------------------------------------------

    def test_extra_fields_ignored(self) -> None:
        """Extra fields are silently ignored."""
        record = ModelProvenanceDecisionRecord(
            decision_id=DECISION_ID,
            decision_type="model_select",
            timestamp=FIXED_TIMESTAMP,
            candidates_considered=[],
            constraints_applied={},
            scoring_breakdown=[],
            selected_candidate="a",
            reproducibility_snapshot={},
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(record, "unknown_field")

    # -----------------------------------------------------------------------
    # from_attributes=True
    # -----------------------------------------------------------------------

    def test_from_attributes(self) -> None:
        """Model can be constructed from ORM-like objects."""

        class FakeOrm:
            decision_id = DECISION_ID
            decision_type = "tool_pick"
            timestamp = FIXED_TIMESTAMP
            candidates_considered = ["bash", "read"]
            constraints_applied: dict[str, str] = {}
            scoring_breakdown: list[ModelProvenanceDecisionScore] = []
            tie_breaker = None
            selected_candidate = "bash"
            agent_rationale = None
            reproducibility_snapshot: dict[str, str] = {}

        record = ModelProvenanceDecisionRecord.model_validate(
            FakeOrm(), from_attributes=True
        )
        assert record.decision_type == "tool_pick"
        assert record.selected_candidate == "bash"

    # -----------------------------------------------------------------------
    # Scoring breakdown nested model integration
    # -----------------------------------------------------------------------

    def test_scoring_breakdown_contains_score_models(self) -> None:
        """Scoring breakdown entries are ModelProvenanceDecisionScore instances."""
        score = make_score("claude-3-opus", 0.9, {"quality": 0.9})
        record = make_record(scoring_breakdown=[score])
        assert isinstance(record.scoring_breakdown[0], ModelProvenanceDecisionScore)
        assert record.scoring_breakdown[0].candidate == "claude-3-opus"

    def test_scoring_breakdown_dict_coercion(self) -> None:
        """Scoring breakdown entries can be supplied as raw dicts (Pydantic coerces)."""
        raw_score = {"candidate": "gpt-4", "score": 0.75, "breakdown": {"q": 0.75}}
        record = ModelProvenanceDecisionRecord(
            decision_id=DECISION_ID,
            decision_type="model_select",
            timestamp=FIXED_TIMESTAMP,
            candidates_considered=["gpt-4"],
            constraints_applied={},
            scoring_breakdown=[raw_score],  # type: ignore[list-item]
            selected_candidate="gpt-4",
            reproducibility_snapshot={},
        )
        assert record.scoring_breakdown[0].candidate == "gpt-4"

    # -----------------------------------------------------------------------
    # Reproducibility snapshot
    # -----------------------------------------------------------------------

    def test_reproducibility_snapshot_stores_values(self) -> None:
        """Reproducibility snapshot stores key-value pairs correctly."""
        snapshot = {
            "routing_version": "1.2.3",
            "model_registry_hash": "abc123",
            "feature_flags": "flag-a=true,flag-b=false",
        }
        record = make_record(reproducibility_snapshot=snapshot)
        assert record.reproducibility_snapshot == snapshot

    # -----------------------------------------------------------------------
    # Cross-validation: selected_candidate vs candidates_considered
    # -----------------------------------------------------------------------

    def test_selected_candidate_not_in_candidates_raises(self) -> None:
        """selected_candidate not in candidates_considered raises ValidationError."""
        with pytest.raises(ValidationError, match="selected_candidate"):
            make_record(
                candidates_considered=["claude-3-opus", "gpt-4"],
                selected_candidate="gemini-pro",
            )

    def test_selected_candidate_in_candidates_valid(self) -> None:
        """selected_candidate present in candidates_considered is valid."""
        record = make_record(
            candidates_considered=["claude-3-opus", "gpt-4"],
            selected_candidate="gpt-4",
        )
        assert record.selected_candidate == "gpt-4"

    def test_selected_candidate_allowed_when_candidates_empty(self) -> None:
        """selected_candidate is allowed when candidates_considered is empty (edge case).

        scoring_breakdown must also be empty when candidates_considered is empty.
        """
        record = make_record(
            candidates_considered=[],
            selected_candidate="any-candidate",
            scoring_breakdown=[],
        )
        assert record.selected_candidate == "any-candidate"

    def test_scoring_breakdown_unknown_candidate_raises(self) -> None:
        """scoring_breakdown entry with candidate not in candidates_considered raises ValidationError."""
        unknown_score = make_score("gemini-pro", 0.6, {"quality": 0.6})
        with pytest.raises(ValidationError, match="scoring_breakdown candidate"):
            make_record(
                candidates_considered=["claude-3-opus", "gpt-4"],
                selected_candidate="claude-3-opus",
                scoring_breakdown=[unknown_score],
            )

    def test_scoring_breakdown_valid_candidate_passes(self) -> None:
        """scoring_breakdown entry whose candidate is in candidates_considered passes validation."""
        valid_score = make_score("gpt-4", 0.75, {"quality": 0.75})
        record = make_record(
            candidates_considered=["claude-3-opus", "gpt-4"],
            selected_candidate="claude-3-opus",
            scoring_breakdown=[valid_score],
        )
        assert record.scoring_breakdown[0].candidate == "gpt-4"

    def test_nonempty_scoring_breakdown_with_empty_candidates_raises(self) -> None:
        """Non-empty scoring_breakdown with empty candidates_considered is logically
        inconsistent and raises ValidationError."""
        with pytest.raises(ValidationError, match="scoring_breakdown must be empty"):
            make_record(
                candidates_considered=[],
                selected_candidate="any-candidate",
                scoring_breakdown=[make_score("any-candidate")],
            )

    def test_empty_string_in_candidates_considered_raises(self) -> None:
        """Empty string element in candidates_considered raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            make_record(
                candidates_considered=["claude-3-opus", ""],
                selected_candidate="claude-3-opus",
                scoring_breakdown=[],
            )


# ===========================================================================
# Tests: R3 — Export paths
# ===========================================================================


@pytest.mark.unit
class TestExportPaths:
    """Verify R3: DecisionRecord and DecisionScore are importable from
    omnibase_core.contracts and omnibase_core.models.contracts."""

    def test_decision_record_importable_from_contracts(self) -> None:
        """DecisionRecord is importable from omnibase_core.contracts."""
        from omnibase_core.contracts import DecisionRecord as ImportedDecisionRecord

        assert ImportedDecisionRecord is ModelProvenanceDecisionRecord

    def test_decision_score_importable_from_contracts(self) -> None:
        """DecisionScore is importable from omnibase_core.contracts."""
        from omnibase_core.contracts import DecisionScore as ImportedDecisionScore

        assert ImportedDecisionScore is ModelProvenanceDecisionScore

    def test_decision_record_importable_from_models_contracts(self) -> None:
        """DecisionRecord is importable from omnibase_core.models.contracts."""
        from omnibase_core.models.contracts import (
            DecisionRecord as ModelsDecisionRecord,
        )

        assert ModelsDecisionRecord is ModelProvenanceDecisionRecord

    def test_decision_score_importable_from_models_contracts(self) -> None:
        """DecisionScore is importable from omnibase_core.models.contracts."""
        from omnibase_core.models.contracts import DecisionScore as ModelsDecisionScore

        assert ModelsDecisionScore is ModelProvenanceDecisionScore

    def test_decision_record_in_contracts_all(self) -> None:
        """DecisionRecord appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "DecisionRecord" in contracts_module.__all__

    def test_decision_score_in_contracts_all(self) -> None:
        """DecisionScore appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "DecisionScore" in contracts_module.__all__

    def test_model_provenance_decision_record_in_contracts_all(self) -> None:
        """ModelProvenanceDecisionRecord appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "ModelProvenanceDecisionRecord" in contracts_module.__all__

    def test_model_provenance_decision_score_in_contracts_all(self) -> None:
        """ModelProvenanceDecisionScore appears in omnibase_core.contracts.__all__."""
        import omnibase_core.contracts as contracts_module

        assert "ModelProvenanceDecisionScore" in contracts_module.__all__

    def test_decision_record_alias_is_same_class(self) -> None:
        """The public alias DecisionRecord is the canonical class."""
        assert DecisionRecord is ModelProvenanceDecisionRecord

    def test_decision_score_alias_is_same_class(self) -> None:
        """The public alias DecisionScore is the canonical class."""
        assert DecisionScore is ModelProvenanceDecisionScore

    def test_instantiation_via_alias(self) -> None:
        """DecisionRecord alias can be used to instantiate models."""
        record = DecisionRecord(
            decision_id=DECISION_ID,
            decision_type="model_select",
            timestamp=FIXED_TIMESTAMP,
            candidates_considered=["a"],
            constraints_applied={},
            scoring_breakdown=[],
            selected_candidate="a",
            reproducibility_snapshot={},
        )
        assert isinstance(record, ModelProvenanceDecisionRecord)

    def test_score_instantiation_via_alias(self) -> None:
        """DecisionScore alias can be used to instantiate models."""
        score = DecisionScore(
            candidate="a",
            score=1.0,
            breakdown={},
        )
        assert isinstance(score, ModelProvenanceDecisionScore)

    def test_models_contracts_all_exports(self) -> None:
        """ModelProvenanceDecisionRecord and ModelProvenanceDecisionScore appear
        in omnibase_core.models.contracts.__all__."""
        import omnibase_core.models.contracts as models_contracts_module

        assert "ModelProvenanceDecisionRecord" in models_contracts_module.__all__
        assert "ModelProvenanceDecisionScore" in models_contracts_module.__all__
