# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Intent Intelligence Framework models (OMN-2486).

Tests cover:
- Instantiation of all 8 frozen Pydantic models.
- Field validation (required fields, range constraints).
- Frozen immutability (mutation raises TypeError).
- Serialization round-trips (model_dump / model_validate).
- Import from omnibase_core.models.intelligence package.
- __all__ membership for all 8 model names.

All tests are marked ``pytest.mark.unit`` for CI shard targeting.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
from omnibase_core.models.intelligence.intent.model_intent_cost_forecast import (
    ModelIntentCostForecast,
)
from omnibase_core.models.intelligence.intent.model_intent_drift_signal import (
    ModelIntentDriftSignal,
)
from omnibase_core.models.intelligence.intent.model_intent_graph_node import (
    ModelIntentGraphNode,
)
from omnibase_core.models.intelligence.intent.model_intent_rollback_trigger import (
    ModelIntentRollbackTrigger,
)
from omnibase_core.models.intelligence.intent.model_intent_to_commit_binding import (
    ModelIntentToCommitBinding,
)
from omnibase_core.models.intelligence.intent.model_intent_transition import (
    ModelIntentTransition,
)
from omnibase_core.models.intelligence.intent.model_typed_intent import ModelTypedIntent
from omnibase_core.models.intelligence.intent.model_user_intent_profile import (
    ModelUserIntentProfile,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
_SESSION_ID = "session-test-001"


# ===========================================================================
# EnumIntentClass
# ===========================================================================


class TestEnumIntentClass:
    """Tests for EnumIntentClass enum definition and values."""

    def test_all_required_values_present(self) -> None:
        """All 8 required intent classes must be present."""
        required = {
            "REFACTOR",
            "BUGFIX",
            "FEATURE",
            "ANALYSIS",
            "CONFIGURATION",
            "DOCUMENTATION",
            "MIGRATION",
            "SECURITY",
        }
        actual = {member.name for member in EnumIntentClass}
        assert required == actual

    def test_string_values_are_lowercase(self) -> None:
        """Enum values must be lowercase strings (ONEX casing standard)."""
        for member in EnumIntentClass:
            assert member.value == member.value.lower()

    def test_str_returns_value(self) -> None:
        """str() must return the enum value (via StrValueHelper mixin)."""
        assert str(EnumIntentClass.REFACTOR) == "refactor"
        assert str(EnumIntentClass.SECURITY) == "security"


# ===========================================================================
# ModelTypedIntent
# ===========================================================================


class TestModelTypedIntentInstantiation:
    """Tests for ModelTypedIntent instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        intent_id = uuid4()
        model = ModelTypedIntent(
            intent_id=intent_id,
            intent_class=EnumIntentClass.BUGFIX,
            session_id=_SESSION_ID,
            prompt_preview="Fix the NPE in authentication flow",
            confidence_score=0.91,
            classified_at=_NOW,
        )
        assert model.intent_id == intent_id
        assert model.intent_class == EnumIntentClass.BUGFIX
        assert model.session_id == _SESSION_ID
        assert model.prompt_preview == "Fix the NPE in authentication flow"
        assert model.confidence_score == 0.91
        assert model.classified_at == _NOW

    def test_confidence_score_at_bounds(self) -> None:
        """Confidence score accepts 0.0 and 1.0."""
        base = {
            "intent_id": uuid4(),
            "intent_class": EnumIntentClass.FEATURE,
            "session_id": _SESSION_ID,
            "prompt_preview": "x",
            "classified_at": _NOW,
        }
        low = ModelTypedIntent(**base, confidence_score=0.0)
        high = ModelTypedIntent(**base, confidence_score=1.0)
        assert low.confidence_score == 0.0
        assert high.confidence_score == 1.0

    def test_confidence_score_out_of_range_fails(self) -> None:
        """Confidence score outside [0.0, 1.0] must fail validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelTypedIntent(
                intent_id=uuid4(),
                intent_class=EnumIntentClass.FEATURE,
                session_id=_SESSION_ID,
                prompt_preview="x",
                confidence_score=1.1,
                classified_at=_NOW,
            )

    def test_prompt_preview_max_length_enforced(self) -> None:
        """prompt_preview exceeding 100 chars must fail validation."""
        from pydantic import ValidationError

        long_preview = "x" * 101
        with pytest.raises(ValidationError):
            ModelTypedIntent(
                intent_id=uuid4(),
                intent_class=EnumIntentClass.ANALYSIS,
                session_id=_SESSION_ID,
                prompt_preview=long_preview,
                confidence_score=0.5,
                classified_at=_NOW,
            )


class TestModelTypedIntentFrozen:
    """Tests for ModelTypedIntent immutability."""

    def test_mutation_raises_type_error(self) -> None:
        """Frozen model must raise TypeError on attribute mutation."""
        model = ModelTypedIntent(
            intent_id=uuid4(),
            intent_class=EnumIntentClass.REFACTOR,
            session_id=_SESSION_ID,
            prompt_preview="Refactor auth module",
            confidence_score=0.85,
            classified_at=_NOW,
        )
        with pytest.raises((TypeError, Exception)):
            model.confidence_score = 0.1  # type: ignore[misc]


class TestModelTypedIntentSerialization:
    """Tests for ModelTypedIntent serialization round-trip."""

    def test_model_dump_round_trip(self) -> None:
        """model_dump then model_validate must produce equal model."""
        original = ModelTypedIntent(
            intent_id=uuid4(),
            intent_class=EnumIntentClass.MIGRATION,
            session_id=_SESSION_ID,
            prompt_preview="Migrate DB to Postgres 16",
            confidence_score=0.77,
            classified_at=_NOW,
        )
        data = original.model_dump()
        restored = ModelTypedIntent.model_validate(data)
        assert original.intent_id == restored.intent_id
        assert original.intent_class == restored.intent_class
        assert original.confidence_score == restored.confidence_score


# ===========================================================================
# ModelIntentDriftSignal
# ===========================================================================


class TestModelIntentDriftSignalInstantiation:
    """Tests for ModelIntentDriftSignal instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        intent_id = uuid4()
        model = ModelIntentDriftSignal(
            intent_id=intent_id,
            drift_type="scope_expansion",
            description="Session now touches 10 files vs expected 2",
            detected_at=_NOW,
            severity=0.6,
        )
        assert model.intent_id == intent_id
        assert model.drift_type == "scope_expansion"
        assert model.severity == 0.6

    def test_all_drift_types_accepted(self) -> None:
        """All three canonical drift types must be accepted."""
        for drift_type in ("tool_mismatch", "file_surface", "scope_expansion"):
            model = ModelIntentDriftSignal(
                intent_id=uuid4(),
                drift_type=drift_type,  # type: ignore[arg-type]
                description="drift",
                detected_at=_NOW,
                severity=0.5,
            )
            assert model.drift_type == drift_type

    def test_invalid_drift_type_fails(self) -> None:
        """Unknown drift type must fail validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentDriftSignal(
                intent_id=uuid4(),
                drift_type="bad_type",  # type: ignore[arg-type]
                description="drift",
                detected_at=_NOW,
                severity=0.5,
            )

    def test_severity_bounds(self) -> None:
        """Severity must be within [0.0, 1.0]."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentDriftSignal(
                intent_id=uuid4(),
                drift_type="tool_mismatch",
                description="drift",
                detected_at=_NOW,
                severity=1.1,
            )


class TestModelIntentDriftSignalFrozen:
    """Tests for ModelIntentDriftSignal immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentDriftSignal(
            intent_id=uuid4(),
            drift_type="file_surface",
            description="files diverged",
            detected_at=_NOW,
            severity=0.3,
        )
        with pytest.raises((TypeError, Exception)):
            model.severity = 0.9  # type: ignore[misc]


# ===========================================================================
# ModelIntentCostForecast
# ===========================================================================


class TestModelIntentCostForecastInstantiation:
    """Tests for ModelIntentCostForecast instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        model = ModelIntentCostForecast(
            intent_class=EnumIntentClass.FEATURE,
            estimated_tokens=4000,
            estimated_cost_usd=0.020,
            estimated_latency_ms=3500,
            confidence_interval=0.15,
            forecasted_at=_NOW,
        )
        assert model.intent_class == EnumIntentClass.FEATURE
        assert model.estimated_tokens == 4000
        assert model.estimated_cost_usd == 0.020
        assert model.estimated_latency_ms == 3500
        assert model.confidence_interval == 0.15
        assert model.forecasted_at == _NOW

    def test_negative_tokens_fails(self) -> None:
        """estimated_tokens must be >= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentCostForecast(
                intent_class=EnumIntentClass.ANALYSIS,
                estimated_tokens=-1,
                estimated_cost_usd=0.01,
                estimated_latency_ms=1000,
                confidence_interval=0.1,
                forecasted_at=_NOW,
            )

    def test_confidence_interval_bounds(self) -> None:
        """confidence_interval must be within [0.0, 1.0]."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentCostForecast(
                intent_class=EnumIntentClass.BUGFIX,
                estimated_tokens=100,
                estimated_cost_usd=0.001,
                estimated_latency_ms=500,
                confidence_interval=1.5,
                forecasted_at=_NOW,
            )


class TestModelIntentCostForecastFrozen:
    """Tests for ModelIntentCostForecast immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentCostForecast(
            intent_class=EnumIntentClass.SECURITY,
            estimated_tokens=2000,
            estimated_cost_usd=0.01,
            estimated_latency_ms=2000,
            confidence_interval=0.2,
            forecasted_at=_NOW,
        )
        with pytest.raises((TypeError, Exception)):
            model.estimated_cost_usd = 99.0  # type: ignore[misc]


# ===========================================================================
# ModelIntentGraphNode
# ===========================================================================


class TestModelIntentGraphNodeInstantiation:
    """Tests for ModelIntentGraphNode instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        node_id = uuid4()
        model = ModelIntentGraphNode(
            node_id=node_id,
            intent_class=EnumIntentClass.REFACTOR,
            session_id=_SESSION_ID,
            occurrence_count=50,
            avg_cost_usd=0.025,
            success_rate=0.90,
        )
        assert model.node_id == node_id
        assert model.intent_class == EnumIntentClass.REFACTOR
        assert model.occurrence_count == 50
        assert model.success_rate == 0.90

    def test_occurrence_count_non_negative(self) -> None:
        """occurrence_count must be >= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentGraphNode(
                node_id=uuid4(),
                intent_class=EnumIntentClass.BUGFIX,
                session_id=_SESSION_ID,
                occurrence_count=-1,
                avg_cost_usd=0.01,
                success_rate=0.5,
            )

    def test_success_rate_bounds(self) -> None:
        """success_rate must be within [0.0, 1.0]."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentGraphNode(
                node_id=uuid4(),
                intent_class=EnumIntentClass.FEATURE,
                session_id=_SESSION_ID,
                occurrence_count=10,
                avg_cost_usd=0.01,
                success_rate=1.5,
            )


class TestModelIntentGraphNodeFrozen:
    """Tests for ModelIntentGraphNode immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentGraphNode(
            node_id=uuid4(),
            intent_class=EnumIntentClass.DOCUMENTATION,
            session_id=_SESSION_ID,
            occurrence_count=5,
            avg_cost_usd=0.005,
            success_rate=1.0,
        )
        with pytest.raises((TypeError, Exception)):
            model.occurrence_count = 999  # type: ignore[misc]


# ===========================================================================
# ModelIntentTransition
# ===========================================================================


class TestModelIntentTransitionInstantiation:
    """Tests for ModelIntentTransition instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        model = ModelIntentTransition(
            from_intent_class=EnumIntentClass.ANALYSIS,
            to_intent_class=EnumIntentClass.REFACTOR,
            transition_count=38,
            avg_success_rate=0.87,
            avg_cost_usd=0.034,
        )
        assert model.from_intent_class == EnumIntentClass.ANALYSIS
        assert model.to_intent_class == EnumIntentClass.REFACTOR
        assert model.transition_count == 38

    def test_self_loop_allowed(self) -> None:
        """Transition from a class to itself must be accepted."""
        model = ModelIntentTransition(
            from_intent_class=EnumIntentClass.BUGFIX,
            to_intent_class=EnumIntentClass.BUGFIX,
            transition_count=5,
            avg_success_rate=0.6,
            avg_cost_usd=0.01,
        )
        assert model.from_intent_class == model.to_intent_class

    def test_transition_count_non_negative(self) -> None:
        """transition_count must be >= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentTransition(
                from_intent_class=EnumIntentClass.FEATURE,
                to_intent_class=EnumIntentClass.BUGFIX,
                transition_count=-1,
                avg_success_rate=0.5,
                avg_cost_usd=0.01,
            )


class TestModelIntentTransitionFrozen:
    """Tests for ModelIntentTransition immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentTransition(
            from_intent_class=EnumIntentClass.CONFIGURATION,
            to_intent_class=EnumIntentClass.SECURITY,
            transition_count=12,
            avg_success_rate=0.75,
            avg_cost_usd=0.02,
        )
        with pytest.raises((TypeError, Exception)):
            model.transition_count = 0  # type: ignore[misc]


# ===========================================================================
# ModelIntentToCommitBinding
# ===========================================================================


class TestModelIntentToCommitBindingInstantiation:
    """Tests for ModelIntentToCommitBinding instantiation."""

    def test_create_minimal(self) -> None:
        """Model can be created with minimum required fields."""
        intent_id = uuid4()
        model = ModelIntentToCommitBinding(
            intent_id=intent_id,
            commit_sha="a3f8c1d2e4b67890123456789012345678901234",
            outcome_label="success",
            bound_at=_NOW,
        )
        assert model.intent_id == intent_id
        assert model.commit_sha == "a3f8c1d2e4b67890123456789012345678901234"
        assert model.plan_id is None
        assert model.tool_call_ids == []
        assert model.outcome_label == "success"

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all optional fields."""
        intent_id = uuid4()
        plan_id = uuid4()
        model = ModelIntentToCommitBinding(
            intent_id=intent_id,
            commit_sha="abc123",
            plan_id=plan_id,
            tool_call_ids=["tc-001", "tc-002"],
            outcome_label="partial",
            bound_at=_NOW,
        )
        assert model.plan_id == plan_id
        assert model.tool_call_ids == ["tc-001", "tc-002"]

    def test_empty_commit_sha_fails(self) -> None:
        """commit_sha must not be empty."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelIntentToCommitBinding(
                intent_id=uuid4(),
                commit_sha="",
                outcome_label="success",
                bound_at=_NOW,
            )


class TestModelIntentToCommitBindingFrozen:
    """Tests for ModelIntentToCommitBinding immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentToCommitBinding(
            intent_id=uuid4(),
            commit_sha="deadbeef",
            outcome_label="reverted",
            bound_at=_NOW,
        )
        with pytest.raises((TypeError, Exception)):
            model.outcome_label = "success"  # type: ignore[misc]


# ===========================================================================
# ModelUserIntentProfile
# ===========================================================================


class TestModelUserIntentProfileInstantiation:
    """Tests for ModelUserIntentProfile instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        model = ModelUserIntentProfile(
            user_id="user-jonah",
            dominant_intent_class=EnumIntentClass.REFACTOR,
            class_distribution={
                "refactor": 0.45,
                "bugfix": 0.30,
                "feature": 0.15,
                "analysis": 0.10,
            },
            avg_session_cost_usd=0.042,
            profile_updated_at=_NOW,
        )
        assert model.user_id == "user-jonah"
        assert model.dominant_intent_class == EnumIntentClass.REFACTOR
        assert model.class_distribution["refactor"] == 0.45

    def test_empty_distribution_defaults(self) -> None:
        """class_distribution defaults to empty dict."""
        model = ModelUserIntentProfile(
            user_id="user-x",
            dominant_intent_class=EnumIntentClass.BUGFIX,
            avg_session_cost_usd=0.01,
            profile_updated_at=_NOW,
        )
        assert model.class_distribution == {}

    def test_negative_avg_cost_fails(self) -> None:
        """avg_session_cost_usd must be >= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelUserIntentProfile(
                user_id="user-x",
                dominant_intent_class=EnumIntentClass.FEATURE,
                avg_session_cost_usd=-0.01,
                profile_updated_at=_NOW,
            )


class TestModelUserIntentProfileFrozen:
    """Tests for ModelUserIntentProfile immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelUserIntentProfile(
            user_id="user-test",
            dominant_intent_class=EnumIntentClass.DOCUMENTATION,
            avg_session_cost_usd=0.005,
            profile_updated_at=_NOW,
        )
        with pytest.raises((TypeError, Exception)):
            model.user_id = "attacker"  # type: ignore[misc]


# ===========================================================================
# ModelIntentRollbackTrigger
# ===========================================================================


class TestModelIntentRollbackTriggerInstantiation:
    """Tests for ModelIntentRollbackTrigger instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Model can be created with all required fields."""
        intent_id = uuid4()
        model = ModelIntentRollbackTrigger(
            intent_id=intent_id,
            trigger_reason="3 unit tests regressed after applying changes",
            outcome_label="test_failure",
            rollback_recommended=True,
            triggered_at=_NOW,
        )
        assert model.intent_id == intent_id
        assert model.trigger_reason == "3 unit tests regressed after applying changes"
        assert model.outcome_label == "test_failure"
        assert model.rollback_recommended is True
        assert model.triggered_at == _NOW

    def test_rollback_not_recommended(self) -> None:
        """rollback_recommended can be False for informational signals."""
        model = ModelIntentRollbackTrigger(
            intent_id=uuid4(),
            trigger_reason="Minor quality score drop",
            outcome_label="quality_regression",
            rollback_recommended=False,
            triggered_at=_NOW,
        )
        assert model.rollback_recommended is False


class TestModelIntentRollbackTriggerFrozen:
    """Tests for ModelIntentRollbackTrigger immutability."""

    def test_mutation_raises(self) -> None:
        """Frozen model must raise on mutation attempt."""
        model = ModelIntentRollbackTrigger(
            intent_id=uuid4(),
            trigger_reason="security violation",
            outcome_label="security_violation",
            rollback_recommended=True,
            triggered_at=_NOW,
        )
        with pytest.raises((TypeError, Exception)):
            model.rollback_recommended = False  # type: ignore[misc]


# ===========================================================================
# Import and __all__ tests
# ===========================================================================


class TestIntentIntelligenceModelsImports:
    """Tests for imports from omnibase_core.models.intelligence package."""

    def test_import_all_8_models_from_intelligence(self) -> None:
        """All 8 models must be importable from the intelligence package."""
        from omnibase_core.models.intelligence import ModelIntentCostForecast as C
        from omnibase_core.models.intelligence import ModelIntentDriftSignal as D
        from omnibase_core.models.intelligence import ModelIntentGraphNode as G
        from omnibase_core.models.intelligence import ModelIntentRollbackTrigger as R
        from omnibase_core.models.intelligence import ModelIntentToCommitBinding as B
        from omnibase_core.models.intelligence import ModelIntentTransition as T
        from omnibase_core.models.intelligence import ModelTypedIntent as I
        from omnibase_core.models.intelligence import ModelUserIntentProfile as U

        assert C is ModelIntentCostForecast
        assert D is ModelIntentDriftSignal
        assert G is ModelIntentGraphNode
        assert R is ModelIntentRollbackTrigger
        assert B is ModelIntentToCommitBinding
        assert T is ModelIntentTransition
        assert I is ModelTypedIntent
        assert U is ModelUserIntentProfile

    def test_all_8_model_names_in_intelligence_all(self) -> None:
        """All 8 model names must appear in intelligence.__all__."""
        from omnibase_core.models import intelligence

        expected = {
            "ModelTypedIntent",
            "ModelIntentDriftSignal",
            "ModelIntentCostForecast",
            "ModelIntentGraphNode",
            "ModelIntentTransition",
            "ModelIntentToCommitBinding",
            "ModelUserIntentProfile",
            "ModelIntentRollbackTrigger",
        }
        for name in expected:
            assert name in intelligence.__all__, (
                f"{name!r} missing from intelligence.__all__"
            )

    def test_import_from_intent_subpackage(self) -> None:
        """Models must also be importable from the intent subpackage directly."""
        from omnibase_core.models.intelligence.intent import (
            ModelIntentCostForecast,
            ModelIntentDriftSignal,
            ModelIntentGraphNode,
            ModelIntentRollbackTrigger,
            ModelIntentToCommitBinding,
            ModelIntentTransition,
            ModelTypedIntent,
            ModelUserIntentProfile,
        )

        # Verify they are the concrete classes
        assert ModelTypedIntent.__name__ == "ModelTypedIntent"
        assert ModelIntentDriftSignal.__name__ == "ModelIntentDriftSignal"
        assert ModelIntentCostForecast.__name__ == "ModelIntentCostForecast"
        assert ModelIntentGraphNode.__name__ == "ModelIntentGraphNode"
        assert ModelIntentTransition.__name__ == "ModelIntentTransition"
        assert ModelIntentToCommitBinding.__name__ == "ModelIntentToCommitBinding"
        assert ModelUserIntentProfile.__name__ == "ModelUserIntentProfile"
        assert ModelIntentRollbackTrigger.__name__ == "ModelIntentRollbackTrigger"

    def test_enum_intent_class_importable_from_enums_intelligence(self) -> None:
        """EnumIntentClass must be importable from enums.intelligence."""
        from omnibase_core.enums.intelligence import EnumIntentClass as E

        assert E is EnumIntentClass
