# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for enforcement-related models for replay safety infrastructure.

Tests cover:
- ModelEnforcementDecision creation and validation
- ModelAuditTrailEntry creation and validation
- ModelAuditTrailSummary creation and validation
- frozen=True prevents modification
- from_attributes=True works with ORM-style access

OMN-1150: Replay Safety Enforcement

.. versionadded:: 0.6.3
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)
from omnibase_core.models.replay.model_audit_trail_entry import ModelAuditTrailEntry
from omnibase_core.models.replay.model_audit_trail_summary import ModelAuditTrailSummary
from omnibase_core.models.replay.model_enforcement_decision import (
    ModelEnforcementDecision,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_timestamp() -> datetime:
    """Create sample timestamp."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)


@pytest.fixture
def sample_decision(sample_timestamp: datetime) -> ModelEnforcementDecision:
    """Create a sample enforcement decision."""
    return ModelEnforcementDecision(
        effect_type="time.now",
        determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        source=EnumNonDeterministicSource.TIME,
        mode=EnumEnforcementMode.STRICT,
        decision="blocked",
        reason="Time effects blocked in strict mode",
        timestamp=sample_timestamp,
    )


@pytest.fixture
def sample_entry(sample_decision: ModelEnforcementDecision) -> ModelAuditTrailEntry:
    """Create a sample audit trail entry."""
    return ModelAuditTrailEntry(
        id=uuid4(),
        session_id=uuid4(),
        sequence_number=0,
        decision=sample_decision,
        context={"handler": "my_handler"},
    )


@pytest.fixture
def sample_summary() -> ModelAuditTrailSummary:
    """Create a sample audit trail summary."""
    return ModelAuditTrailSummary(
        session_id=uuid4(),
        total_decisions=10,
        decisions_by_outcome={"allowed": 6, "blocked": 2, "mocked": 2},
        decisions_by_source={"time": 3, "random": 2, "network": 5},
        decisions_by_mode={"strict": 8, "mocked": 2},
        first_decision_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
        last_decision_at=datetime(2024, 6, 15, 12, 5, 0, tzinfo=UTC),
        blocked_effects=["http.get", "file.read"],
    )


# =============================================================================
# TEST MODEL_ENFORCEMENT_DECISION CREATION
# =============================================================================


@pytest.mark.unit
class TestModelEnforcementDecisionCreation:
    """Tests for ModelEnforcementDecision creation."""

    def test_create_basic_decision(self, sample_timestamp: datetime) -> None:
        """Test creating a basic enforcement decision."""
        decision = ModelEnforcementDecision(
            effect_type="http.get",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.NETWORK,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Network effects blocked",
            timestamp=sample_timestamp,
        )

        assert decision.effect_type == "http.get"
        assert decision.determinism == EnumEffectDeterminism.NON_DETERMINISTIC
        assert decision.source == EnumNonDeterministicSource.NETWORK
        assert decision.mode == EnumEnforcementMode.STRICT
        assert decision.decision == "blocked"
        assert decision.reason == "Network effects blocked"
        assert decision.timestamp == sample_timestamp

    def test_create_decision_with_mock(self, sample_timestamp: datetime) -> None:
        """Test creating a decision with mock injection."""
        decision = ModelEnforcementDecision(
            effect_type="random.random",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.RANDOM,
            mode=EnumEnforcementMode.MOCKED,
            decision="mocked",
            reason="Random effect mocked",
            timestamp=sample_timestamp,
            mock_injected=True,
            original_value=None,
            mocked_value=0.5,
        )

        assert decision.mock_injected is True
        assert decision.mocked_value == 0.5

    def test_create_decision_with_original_value(
        self, sample_timestamp: datetime
    ) -> None:
        """Test creating a decision with original value captured."""
        decision = ModelEnforcementDecision(
            effect_type="time.now",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.TIME,
            mode=EnumEnforcementMode.MOCKED,
            decision="mocked",
            reason="Time effect mocked",
            timestamp=sample_timestamp,
            mock_injected=True,
            original_value=datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC),
            mocked_value=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

        assert decision.original_value is not None
        assert decision.mocked_value is not None

    def test_create_deterministic_decision(self, sample_timestamp: datetime) -> None:
        """Test creating a decision for deterministic effect."""
        decision = ModelEnforcementDecision(
            effect_type="compute.hash",
            determinism=EnumEffectDeterminism.DETERMINISTIC,
            source=None,
            mode=EnumEnforcementMode.STRICT,
            decision="allowed",
            reason="Effect is deterministic",
            timestamp=sample_timestamp,
        )

        assert decision.source is None
        assert decision.decision == "allowed"


# =============================================================================
# TEST MODEL_ENFORCEMENT_DECISION VALIDATION
# =============================================================================


@pytest.mark.unit
class TestModelEnforcementDecisionValidation:
    """Tests for ModelEnforcementDecision validation."""

    def test_required_field_effect_type(self, sample_timestamp: datetime) -> None:
        """Test that effect_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                mode=EnumEnforcementMode.STRICT,
                decision="blocked",
                reason="Test",
                timestamp=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "effect_type" in str(exc_info.value)

    def test_required_field_determinism(self, sample_timestamp: datetime) -> None:
        """Test that determinism is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                mode=EnumEnforcementMode.STRICT,
                decision="blocked",
                reason="Test",
                timestamp=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "determinism" in str(exc_info.value)

    def test_required_field_mode(self, sample_timestamp: datetime) -> None:
        """Test that mode is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                decision="blocked",
                reason="Test",
                timestamp=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "mode" in str(exc_info.value)

    def test_required_field_decision(self, sample_timestamp: datetime) -> None:
        """Test that decision is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                mode=EnumEnforcementMode.STRICT,
                reason="Test",
                timestamp=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "decision" in str(exc_info.value)

    def test_required_field_reason(self, sample_timestamp: datetime) -> None:
        """Test that reason is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                mode=EnumEnforcementMode.STRICT,
                decision="blocked",
                timestamp=sample_timestamp,
            )  # type: ignore[call-arg]

        assert "reason" in str(exc_info.value)

    def test_required_field_timestamp(self) -> None:
        """Test that timestamp is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                mode=EnumEnforcementMode.STRICT,
                decision="blocked",
                reason="Test",
            )  # type: ignore[call-arg]

        assert "timestamp" in str(exc_info.value)

    def test_extra_fields_forbidden(self, sample_timestamp: datetime) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnforcementDecision(
                effect_type="test.effect",
                determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
                mode=EnumEnforcementMode.STRICT,
                decision="blocked",
                reason="Test",
                timestamp=sample_timestamp,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert (
            "unknown_field" in str(exc_info.value)
            or "extra" in str(exc_info.value).lower()
        )

    def test_default_mock_injected_is_false(self, sample_timestamp: datetime) -> None:
        """Test that mock_injected defaults to False."""
        decision = ModelEnforcementDecision(
            effect_type="test.effect",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Test",
            timestamp=sample_timestamp,
        )

        assert decision.mock_injected is False

    def test_default_source_is_none(self, sample_timestamp: datetime) -> None:
        """Test that source defaults to None."""
        decision = ModelEnforcementDecision(
            effect_type="test.effect",
            determinism=EnumEffectDeterminism.UNKNOWN,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Test",
            timestamp=sample_timestamp,
        )

        assert decision.source is None


# =============================================================================
# TEST MODEL_ENFORCEMENT_DECISION IMMUTABILITY
# =============================================================================


@pytest.mark.unit
class TestModelEnforcementDecisionImmutability:
    """Tests for ModelEnforcementDecision immutability (frozen=True)."""

    def test_cannot_modify_effect_type(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that effect_type cannot be modified."""
        with pytest.raises(ValidationError):
            sample_decision.effect_type = "modified.type"

    def test_cannot_modify_decision(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that decision cannot be modified."""
        with pytest.raises(ValidationError):
            sample_decision.decision = "allowed"

    def test_cannot_modify_reason(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that reason cannot be modified."""
        with pytest.raises(ValidationError):
            sample_decision.reason = "Modified reason"

    def test_cannot_modify_timestamp(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that timestamp cannot be modified."""
        with pytest.raises(ValidationError):
            sample_decision.timestamp = datetime.now(UTC)


# =============================================================================
# TEST MODEL_ENFORCEMENT_DECISION FROM_ATTRIBUTES
# =============================================================================


@pytest.mark.unit
class TestModelEnforcementDecisionFromAttributes:
    """Tests for ModelEnforcementDecision from_attributes support."""

    def test_from_attributes_with_object(self, sample_timestamp: datetime) -> None:
        """Test that from_attributes works with object-like access."""

        class MockObject:
            effect_type = "test.effect"
            determinism = EnumEffectDeterminism.NON_DETERMINISTIC
            source = None
            mode = EnumEnforcementMode.STRICT
            decision = "blocked"
            reason = "Test reason"
            timestamp = sample_timestamp
            mock_injected = False
            original_value = None
            mocked_value = None

        obj = MockObject()
        decision = ModelEnforcementDecision.model_validate(obj)

        assert decision.effect_type == "test.effect"
        assert decision.decision == "blocked"


# =============================================================================
# TEST MODEL_ENFORCEMENT_DECISION SERIALIZATION
# =============================================================================


@pytest.mark.unit
class TestModelEnforcementDecisionSerialization:
    """Tests for ModelEnforcementDecision serialization."""

    def test_serialization_roundtrip(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test serialization roundtrip."""
        data = sample_decision.model_dump()
        restored = ModelEnforcementDecision.model_validate(data)

        assert restored.effect_type == sample_decision.effect_type
        assert restored.determinism == sample_decision.determinism
        assert restored.decision == sample_decision.decision

    def test_json_serialization_roundtrip(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test JSON serialization roundtrip."""
        json_str = sample_decision.model_dump_json()
        restored = ModelEnforcementDecision.model_validate_json(json_str)

        assert restored.effect_type == sample_decision.effect_type


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_ENTRY CREATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailEntryCreation:
    """Tests for ModelAuditTrailEntry creation."""

    def test_create_basic_entry(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test creating a basic audit trail entry."""
        entry_id = uuid4()
        session_id = uuid4()
        entry = ModelAuditTrailEntry(
            id=entry_id,
            session_id=session_id,
            sequence_number=0,
            decision=sample_decision,
        )

        assert entry.id == entry_id
        assert entry.session_id == session_id
        assert entry.sequence_number == 0
        assert entry.decision == sample_decision

    def test_create_entry_with_context(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test creating entry with context."""
        context = {"handler": "my_handler", "input_hash": "abc123"}
        entry = ModelAuditTrailEntry(
            id=uuid4(),
            session_id=uuid4(),
            sequence_number=0,
            decision=sample_decision,
            context=context,
        )

        assert entry.context == context

    def test_default_context_is_empty_dict(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that default context is empty dict."""
        entry = ModelAuditTrailEntry(
            id=uuid4(),
            session_id=uuid4(),
            sequence_number=0,
            decision=sample_decision,
        )

        assert entry.context == {}


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_ENTRY VALIDATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailEntryValidation:
    """Tests for ModelAuditTrailEntry validation."""

    def test_required_field_id(self, sample_decision: ModelEnforcementDecision) -> None:
        """Test that id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailEntry(
                session_id=uuid4(),
                sequence_number=0,
                decision=sample_decision,
            )  # type: ignore[call-arg]

        assert "id" in str(exc_info.value)

    def test_required_field_session_id(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailEntry(
                id=uuid4(),
                sequence_number=0,
                decision=sample_decision,
            )  # type: ignore[call-arg]

        assert "session_id" in str(exc_info.value)

    def test_required_field_sequence_number(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that sequence_number is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailEntry(
                id=uuid4(),
                session_id=uuid4(),
                decision=sample_decision,
            )  # type: ignore[call-arg]

        assert "sequence_number" in str(exc_info.value)

    def test_required_field_decision(self) -> None:
        """Test that decision is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailEntry(
                id=uuid4(),
                session_id=uuid4(),
                sequence_number=0,
            )  # type: ignore[call-arg]

        assert "decision" in str(exc_info.value)

    def test_sequence_number_must_be_non_negative(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that sequence_number must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailEntry(
                id=uuid4(),
                session_id=uuid4(),
                sequence_number=-1,
                decision=sample_decision,
            )

        assert "sequence_number" in str(exc_info.value)


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_ENTRY IMMUTABILITY
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailEntryImmutability:
    """Tests for ModelAuditTrailEntry immutability (frozen=True)."""

    def test_cannot_modify_id(self, sample_entry: ModelAuditTrailEntry) -> None:
        """Test that id cannot be modified."""
        with pytest.raises(ValidationError):
            sample_entry.id = uuid4()

    def test_cannot_modify_session_id(self, sample_entry: ModelAuditTrailEntry) -> None:
        """Test that session_id cannot be modified."""
        with pytest.raises(ValidationError):
            sample_entry.session_id = uuid4()

    def test_cannot_modify_sequence_number(
        self, sample_entry: ModelAuditTrailEntry
    ) -> None:
        """Test that sequence_number cannot be modified."""
        with pytest.raises(ValidationError):
            sample_entry.sequence_number = 999


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_ENTRY FROM_ATTRIBUTES
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailEntryFromAttributes:
    """Tests for ModelAuditTrailEntry from_attributes support."""

    def test_from_attributes_with_object(
        self, sample_decision: ModelEnforcementDecision
    ) -> None:
        """Test that from_attributes works with object-like access."""
        test_entry_id = uuid4()
        test_session_id = uuid4()

        class MockObject:
            id = test_entry_id
            session_id = test_session_id
            sequence_number = 0
            decision = sample_decision
            context: dict[str, Any] = {}

        obj = MockObject()
        entry = ModelAuditTrailEntry.model_validate(obj)

        assert entry.id == test_entry_id
        assert entry.session_id == test_session_id


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_ENTRY SERIALIZATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailEntrySerialization:
    """Tests for ModelAuditTrailEntry serialization."""

    def test_serialization_roundtrip(self, sample_entry: ModelAuditTrailEntry) -> None:
        """Test serialization roundtrip."""
        data = sample_entry.model_dump()
        restored = ModelAuditTrailEntry.model_validate(data)

        assert restored.id == sample_entry.id
        assert restored.session_id == sample_entry.session_id

    def test_json_serialization_roundtrip(
        self, sample_entry: ModelAuditTrailEntry
    ) -> None:
        """Test JSON serialization roundtrip."""
        json_str = sample_entry.model_dump_json()
        restored = ModelAuditTrailEntry.model_validate_json(json_str)

        assert restored.id == sample_entry.id


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_SUMMARY CREATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailSummaryCreation:
    """Tests for ModelAuditTrailSummary creation."""

    def test_create_basic_summary(self) -> None:
        """Test creating a basic audit trail summary."""
        test_session_id = uuid4()
        summary = ModelAuditTrailSummary(
            session_id=test_session_id,
            total_decisions=5,
        )

        assert summary.session_id == test_session_id
        assert summary.total_decisions == 5
        assert summary.decisions_by_outcome == {}
        assert summary.decisions_by_source == {}
        assert summary.decisions_by_mode == {}
        assert summary.blocked_effects == []

    def test_create_full_summary(self, sample_summary: ModelAuditTrailSummary) -> None:
        """Test creating a full summary with all fields."""
        assert isinstance(sample_summary.session_id, UUID)
        assert sample_summary.total_decisions == 10
        assert sample_summary.decisions_by_outcome["allowed"] == 6
        assert sample_summary.decisions_by_source["time"] == 3
        assert sample_summary.decisions_by_mode["strict"] == 8
        assert sample_summary.first_decision_at is not None
        assert sample_summary.last_decision_at is not None
        assert len(sample_summary.blocked_effects) == 2


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_SUMMARY VALIDATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailSummaryValidation:
    """Tests for ModelAuditTrailSummary validation."""

    def test_required_field_session_id(self) -> None:
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailSummary(
                total_decisions=5,
            )  # type: ignore[call-arg]

        assert "session_id" in str(exc_info.value)

    def test_required_field_total_decisions(self) -> None:
        """Test that total_decisions is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailSummary(
                session_id="session-abc",
            )  # type: ignore[call-arg]

        assert "total_decisions" in str(exc_info.value)

    def test_total_decisions_must_be_non_negative(self) -> None:
        """Test that total_decisions must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAuditTrailSummary(
                session_id=uuid4(),
                total_decisions=-1,
            )

        assert "total_decisions" in str(exc_info.value)


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_SUMMARY IMMUTABILITY
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailSummaryImmutability:
    """Tests for ModelAuditTrailSummary immutability (frozen=True)."""

    def test_cannot_modify_session_id(
        self, sample_summary: ModelAuditTrailSummary
    ) -> None:
        """Test that session_id cannot be modified."""
        with pytest.raises(ValidationError):
            sample_summary.session_id = "modified-session"

    def test_cannot_modify_total_decisions(
        self, sample_summary: ModelAuditTrailSummary
    ) -> None:
        """Test that total_decisions cannot be modified."""
        with pytest.raises(ValidationError):
            sample_summary.total_decisions = 999


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_SUMMARY FROM_ATTRIBUTES
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailSummaryFromAttributes:
    """Tests for ModelAuditTrailSummary from_attributes support."""

    def test_from_attributes_with_object(self) -> None:
        """Test that from_attributes works with object-like access."""
        test_session_id = uuid4()

        class MockObject:
            session_id = test_session_id
            total_decisions = 5
            decisions_by_outcome: dict[str, int] = {}
            decisions_by_source: dict[str, int] = {}
            decisions_by_mode: dict[str, int] = {}
            first_decision_at = None
            last_decision_at = None
            blocked_effects: list[str] = []

        obj = MockObject()
        summary = ModelAuditTrailSummary.model_validate(obj)

        assert summary.session_id == test_session_id
        assert summary.total_decisions == 5


# =============================================================================
# TEST MODEL_AUDIT_TRAIL_SUMMARY SERIALIZATION
# =============================================================================


@pytest.mark.unit
class TestModelAuditTrailSummarySerialization:
    """Tests for ModelAuditTrailSummary serialization."""

    def test_serialization_roundtrip(
        self, sample_summary: ModelAuditTrailSummary
    ) -> None:
        """Test serialization roundtrip."""
        data = sample_summary.model_dump()
        restored = ModelAuditTrailSummary.model_validate(data)

        assert restored.session_id == sample_summary.session_id
        assert restored.total_decisions == sample_summary.total_decisions

    def test_json_serialization_roundtrip(
        self, sample_summary: ModelAuditTrailSummary
    ) -> None:
        """Test JSON serialization roundtrip."""
        json_str = sample_summary.model_dump_json()
        restored = ModelAuditTrailSummary.model_validate_json(json_str)

        assert restored.session_id == sample_summary.session_id


# =============================================================================
# TEST INTER-MODEL RELATIONSHIPS
# =============================================================================


@pytest.mark.unit
class TestInterModelRelationships:
    """Tests for relationships between enforcement models."""

    def test_entry_contains_decision(self, sample_entry: ModelAuditTrailEntry) -> None:
        """Test that entry contains decision."""
        assert isinstance(sample_entry.decision, ModelEnforcementDecision)
        assert sample_entry.decision.effect_type == "time.now"

    def test_nested_decision_is_immutable(
        self, sample_entry: ModelAuditTrailEntry
    ) -> None:
        """Test that nested decision is also immutable."""
        with pytest.raises(ValidationError):
            sample_entry.decision.effect_type = "modified.type"

    def test_models_can_be_compared(
        self,
        sample_decision: ModelEnforcementDecision,
        sample_timestamp: datetime,
    ) -> None:
        """Test that models can be compared for equality."""
        decision2 = ModelEnforcementDecision(
            effect_type="time.now",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.TIME,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Time effects blocked in strict mode",
            timestamp=sample_timestamp,
        )

        assert sample_decision == decision2
