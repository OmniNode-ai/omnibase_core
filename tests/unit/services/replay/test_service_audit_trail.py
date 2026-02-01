# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ServiceAuditTrail - Service for tracking enforcement decisions.

Tests cover:
- record() creates entries with sequence numbers
- get_entries() with no filters
- get_entries() with outcome filter
- get_entries() with source filter
- get_entries() with limit
- get_summary() calculates correct statistics
- export_json() produces valid JSON
- clear() removes all entries
- session_id auto-generation

OMN-1150: Replay Safety Enforcement

.. versionadded:: 0.6.3
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)
from omnibase_core.models.replay.model_enforcement_decision import (
    ModelEnforcementDecision,
)
from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail

# =============================================================================
# FIXTURES
# =============================================================================

# Fixed UUID for consistent testing
TEST_SESSION_UUID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def audit_trail() -> ServiceAuditTrail:
    """Create an audit trail service with fixed session ID."""
    return ServiceAuditTrail(session_id=TEST_SESSION_UUID)


@pytest.fixture
def sample_decision_time() -> ModelEnforcementDecision:
    """Create a sample enforcement decision for time effect."""
    return ModelEnforcementDecision(
        effect_type="time.now",
        determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        source=EnumNonDeterministicSource.TIME,
        mode=EnumEnforcementMode.STRICT,
        decision="blocked",
        reason="Time effects blocked in strict mode",
        timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_decision_network() -> ModelEnforcementDecision:
    """Create a sample enforcement decision for network effect."""
    return ModelEnforcementDecision(
        effect_type="http.get",
        determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        source=EnumNonDeterministicSource.NETWORK,
        mode=EnumEnforcementMode.PERMISSIVE,
        decision="allowed",
        reason="Network effect allowed with audit",
        timestamp=datetime(2024, 6, 15, 12, 1, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_decision_deterministic() -> ModelEnforcementDecision:
    """Create a sample enforcement decision for deterministic effect."""
    return ModelEnforcementDecision(
        effect_type="compute.hash",
        determinism=EnumEffectDeterminism.DETERMINISTIC,
        source=None,
        mode=EnumEnforcementMode.STRICT,
        decision="allowed",
        reason="Effect is deterministic",
        timestamp=datetime(2024, 6, 15, 12, 2, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_decision_mocked() -> ModelEnforcementDecision:
    """Create a sample enforcement decision for mocked effect."""
    return ModelEnforcementDecision(
        effect_type="random.random",
        determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        source=EnumNonDeterministicSource.RANDOM,
        mode=EnumEnforcementMode.MOCKED,
        decision="mocked",
        reason="Random effect mocked",
        timestamp=datetime(2024, 6, 15, 12, 3, 0, tzinfo=UTC),
        mock_injected=True,
        mocked_value=0.5,
    )


# =============================================================================
# TEST RECORD
# =============================================================================


@pytest.mark.unit
class TestRecord:
    """Tests for record() method."""

    def test_record_creates_entry(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test that record creates an entry."""
        entry = audit_trail.record(sample_decision_time)

        assert entry is not None
        assert entry.decision == sample_decision_time

    def test_record_assigns_sequence_numbers(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test that record assigns sequential sequence numbers."""
        entry1 = audit_trail.record(sample_decision_time)
        entry2 = audit_trail.record(sample_decision_network)

        assert entry1.sequence_number == 0
        assert entry2.sequence_number == 1

    def test_record_uses_session_id(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test that record uses the service's session ID."""
        entry = audit_trail.record(sample_decision_time)

        assert entry.session_id == TEST_SESSION_UUID

    def test_record_generates_unique_entry_ids(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test that record generates unique entry IDs."""
        entry1 = audit_trail.record(sample_decision_time)
        entry2 = audit_trail.record(sample_decision_network)

        assert entry1.id != entry2.id

    def test_record_with_context(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test that record includes optional context."""
        context = {"handler": "my_handler", "input_hash": "abc123"}
        entry = audit_trail.record(sample_decision_time, context=context)

        assert entry.context == context

    def test_record_with_empty_context(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test that record handles empty context."""
        entry = audit_trail.record(sample_decision_time)

        assert entry.context == {}

    def test_record_increments_entry_count(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test that record increments entry count."""
        assert audit_trail.entry_count == 0

        _ = audit_trail.record(sample_decision_time)
        assert audit_trail.entry_count == 1

        _ = audit_trail.record(sample_decision_time)
        assert audit_trail.entry_count == 2


# =============================================================================
# TEST GET_ENTRIES
# =============================================================================


@pytest.mark.unit
class TestGetEntries:
    """Tests for get_entries() method."""

    def test_get_entries_no_filters(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with no filters returns all entries."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        entries = audit_trail.get_entries()

        assert len(entries) == 2

    def test_get_entries_empty(self, audit_trail: ServiceAuditTrail) -> None:
        """Test get_entries on empty audit trail."""
        entries = audit_trail.get_entries()

        assert entries == []

    def test_get_entries_with_outcome_filter_blocked(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with outcome filter for blocked."""
        _ = audit_trail.record(sample_decision_time)  # blocked
        _ = audit_trail.record(sample_decision_network)  # allowed

        entries = audit_trail.get_entries(outcome="blocked")

        assert len(entries) == 1
        assert entries[0].decision.decision == "blocked"

    def test_get_entries_with_outcome_filter_allowed(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
        sample_decision_deterministic: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with outcome filter for allowed."""
        _ = audit_trail.record(sample_decision_time)  # blocked
        _ = audit_trail.record(sample_decision_network)  # allowed
        _ = audit_trail.record(sample_decision_deterministic)  # allowed

        entries = audit_trail.get_entries(outcome="allowed")

        assert len(entries) == 2
        assert all(e.decision.decision == "allowed" for e in entries)

    def test_get_entries_with_outcome_filter_mocked(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_mocked: ModelEnforcementDecision,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with outcome filter for mocked."""
        _ = audit_trail.record(sample_decision_mocked)
        _ = audit_trail.record(sample_decision_time)

        entries = audit_trail.get_entries(outcome="mocked")

        assert len(entries) == 1
        assert entries[0].decision.decision == "mocked"

    def test_get_entries_with_source_filter_time(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with source filter for TIME."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        entries = audit_trail.get_entries(source=EnumNonDeterministicSource.TIME)

        assert len(entries) == 1
        assert entries[0].decision.source == EnumNonDeterministicSource.TIME

    def test_get_entries_with_source_filter_network(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with source filter for NETWORK."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        entries = audit_trail.get_entries(source=EnumNonDeterministicSource.NETWORK)

        assert len(entries) == 1
        assert entries[0].decision.source == EnumNonDeterministicSource.NETWORK

    def test_get_entries_with_limit(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with limit."""
        for _ in range(10):
            audit_trail.record(sample_decision_time)

        entries = audit_trail.get_entries(limit=5)

        assert len(entries) == 5

    def test_get_entries_with_limit_greater_than_entries(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with limit greater than entry count."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)

        entries = audit_trail.get_entries(limit=100)

        assert len(entries) == 2

    def test_get_entries_with_combined_filters(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
        sample_decision_deterministic: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries with multiple filters combined."""
        _ = audit_trail.record(sample_decision_time)  # blocked, TIME
        _ = audit_trail.record(sample_decision_network)  # allowed, NETWORK
        _ = audit_trail.record(sample_decision_deterministic)  # allowed, None

        entries = audit_trail.get_entries(
            outcome="blocked", source=EnumNonDeterministicSource.TIME
        )

        assert len(entries) == 1
        assert entries[0].decision.decision == "blocked"
        assert entries[0].decision.source == EnumNonDeterministicSource.TIME

    def test_get_entries_preserves_order(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
        sample_decision_deterministic: ModelEnforcementDecision,
    ) -> None:
        """Test get_entries preserves sequence order."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)
        _ = audit_trail.record(sample_decision_deterministic)

        entries = audit_trail.get_entries()

        assert entries[0].sequence_number == 0
        assert entries[1].sequence_number == 1
        assert entries[2].sequence_number == 2


# =============================================================================
# TEST GET_SUMMARY
# =============================================================================


@pytest.mark.unit
class TestGetSummary:
    """Tests for get_summary() method."""

    def test_get_summary_empty(self, audit_trail: ServiceAuditTrail) -> None:
        """Test get_summary on empty audit trail."""
        summary = audit_trail.get_summary()

        assert summary.session_id == TEST_SESSION_UUID
        assert summary.total_decisions == 0
        assert summary.decisions_by_outcome == {}
        assert summary.decisions_by_source == {}
        assert summary.decisions_by_mode == {}
        assert summary.first_decision_at is None
        assert summary.last_decision_at is None
        assert summary.blocked_effects == []

    def test_get_summary_total_decisions(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary calculates total decisions."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        summary = audit_trail.get_summary()

        assert summary.total_decisions == 2

    def test_get_summary_decisions_by_outcome(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
        sample_decision_mocked: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary calculates decisions by outcome."""
        _ = audit_trail.record(sample_decision_time)  # blocked
        _ = audit_trail.record(sample_decision_network)  # allowed
        _ = audit_trail.record(sample_decision_mocked)  # mocked

        summary = audit_trail.get_summary()

        assert summary.decisions_by_outcome["blocked"] == 1
        assert summary.decisions_by_outcome["allowed"] == 1
        assert summary.decisions_by_outcome["mocked"] == 1

    def test_get_summary_decisions_by_source(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
        sample_decision_deterministic: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary calculates decisions by source."""
        _ = audit_trail.record(sample_decision_time)  # TIME
        _ = audit_trail.record(sample_decision_network)  # NETWORK
        _ = audit_trail.record(sample_decision_deterministic)  # None -> "unknown"

        summary = audit_trail.get_summary()

        assert summary.decisions_by_source["time"] == 1
        assert summary.decisions_by_source["network"] == 1
        assert summary.decisions_by_source["unknown"] == 1

    def test_get_summary_decisions_by_mode(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary calculates decisions by mode."""
        _ = audit_trail.record(sample_decision_time)  # STRICT
        _ = audit_trail.record(sample_decision_network)  # PERMISSIVE

        summary = audit_trail.get_summary()

        assert summary.decisions_by_mode["strict"] == 1
        assert summary.decisions_by_mode["permissive"] == 1

    def test_get_summary_time_range(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary calculates time range."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        summary = audit_trail.get_summary()

        assert summary.first_decision_at == datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        assert summary.last_decision_at == datetime(2024, 6, 15, 12, 1, 0, tzinfo=UTC)

    def test_get_summary_blocked_effects(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary lists blocked effects."""
        _ = audit_trail.record(sample_decision_time)  # blocked
        _ = audit_trail.record(sample_decision_network)  # allowed

        summary = audit_trail.get_summary()

        assert "time.now" in summary.blocked_effects
        assert "http.get" not in summary.blocked_effects

    def test_get_summary_blocked_effects_unique(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test get_summary lists unique blocked effects."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)

        summary = audit_trail.get_summary()

        assert summary.blocked_effects.count("time.now") == 1

    def test_get_summary_blocked_effects_sorted(
        self,
        audit_trail: ServiceAuditTrail,
    ) -> None:
        """Test get_summary returns blocked effects sorted."""
        decision_z = ModelEnforcementDecision(
            effect_type="z.effect",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=None,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Blocked",
            timestamp=datetime.now(UTC),
        )
        decision_a = ModelEnforcementDecision(
            effect_type="a.effect",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=None,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Blocked",
            timestamp=datetime.now(UTC),
        )

        _ = audit_trail.record(decision_z)
        _ = audit_trail.record(decision_a)

        summary = audit_trail.get_summary()

        assert summary.blocked_effects == ["a.effect", "z.effect"]


# =============================================================================
# TEST EXPORT_JSON
# =============================================================================


@pytest.mark.unit
class TestExportJson:
    """Tests for export_json() method."""

    def test_export_json_produces_valid_json(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test export_json produces valid JSON."""
        _ = audit_trail.record(sample_decision_time)

        json_str = audit_trail.export_json()
        data = json.loads(json_str)

        assert data is not None

    def test_export_json_contains_session_id(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test export_json contains session ID."""
        _ = audit_trail.record(sample_decision_time)

        json_str = audit_trail.export_json()
        data = json.loads(json_str)

        assert data["session_id"] == str(TEST_SESSION_UUID)

    def test_export_json_contains_summary(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test export_json contains summary."""
        _ = audit_trail.record(sample_decision_time)

        json_str = audit_trail.export_json()
        data = json.loads(json_str)

        assert "summary" in data
        assert data["summary"]["total_decisions"] == 1

    def test_export_json_contains_entries(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
        sample_decision_network: ModelEnforcementDecision,
    ) -> None:
        """Test export_json contains entries."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_network)

        json_str = audit_trail.export_json()
        data = json.loads(json_str)

        assert "entries" in data
        assert len(data["entries"]) == 2

    def test_export_json_empty_audit_trail(
        self, audit_trail: ServiceAuditTrail
    ) -> None:
        """Test export_json on empty audit trail."""
        json_str = audit_trail.export_json()
        data = json.loads(json_str)

        assert data["session_id"] == str(TEST_SESSION_UUID)
        assert data["summary"]["total_decisions"] == 0
        assert data["entries"] == []

    def test_export_json_is_formatted(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test export_json is properly formatted."""
        _ = audit_trail.record(sample_decision_time)

        json_str = audit_trail.export_json()

        # Should have indentation (formatted)
        assert "\n" in json_str
        assert "  " in json_str


# =============================================================================
# TEST CLEAR
# =============================================================================


@pytest.mark.unit
class TestClear:
    """Tests for clear() method."""

    def test_clear_removes_all_entries(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test clear removes all entries."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)
        assert audit_trail.entry_count == 2

        audit_trail.clear()

        assert audit_trail.entry_count == 0
        assert audit_trail.get_entries() == []

    def test_clear_resets_sequence_counter(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test clear resets sequence counter."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)

        audit_trail.clear()

        entry = audit_trail.record(sample_decision_time)
        assert entry.sequence_number == 0

    def test_clear_preserves_session_id(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test clear preserves session ID."""
        _ = audit_trail.record(sample_decision_time)

        audit_trail.clear()

        assert audit_trail.session_id == TEST_SESSION_UUID


# =============================================================================
# TEST SESSION_ID
# =============================================================================


@pytest.mark.unit
class TestSessionId:
    """Tests for session_id property and auto-generation."""

    def test_session_id_from_constructor(self) -> None:
        """Test session_id from constructor."""
        custom_session_id = uuid4()
        audit_trail = ServiceAuditTrail(session_id=custom_session_id)
        assert audit_trail.session_id == custom_session_id

    def test_session_id_auto_generated(self) -> None:
        """Test session_id is auto-generated if not provided."""
        audit_trail = ServiceAuditTrail()

        assert audit_trail.session_id is not None
        assert isinstance(audit_trail.session_id, UUID)

    def test_session_id_is_uuid_type(self) -> None:
        """Test auto-generated session_id is UUID type."""
        audit_trail = ServiceAuditTrail()

        # session_id should be a UUID instance
        assert isinstance(audit_trail.session_id, UUID)

    def test_different_instances_have_unique_session_ids(self) -> None:
        """Test different instances have unique session IDs."""
        audit_trail1 = ServiceAuditTrail()
        audit_trail2 = ServiceAuditTrail()

        assert audit_trail1.session_id != audit_trail2.session_id


# =============================================================================
# TEST ENTRY_COUNT
# =============================================================================


@pytest.mark.unit
class TestEntryCount:
    """Tests for entry_count property."""

    def test_entry_count_zero_initially(self, audit_trail: ServiceAuditTrail) -> None:
        """Test entry_count is zero initially."""
        assert audit_trail.entry_count == 0

    def test_entry_count_increments(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test entry_count increments with each record."""
        _ = audit_trail.record(sample_decision_time)
        assert audit_trail.entry_count == 1

        _ = audit_trail.record(sample_decision_time)
        assert audit_trail.entry_count == 2

    def test_entry_count_after_clear(
        self,
        audit_trail: ServiceAuditTrail,
        sample_decision_time: ModelEnforcementDecision,
    ) -> None:
        """Test entry_count after clear."""
        _ = audit_trail.record(sample_decision_time)
        _ = audit_trail.record(sample_decision_time)

        audit_trail.clear()

        assert audit_trail.entry_count == 0


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestProtocolCompliance:
    """Tests for ProtocolAuditTrail compliance."""

    def test_implements_record(self) -> None:
        """Test that ServiceAuditTrail implements record()."""
        audit_trail = ServiceAuditTrail()
        decision = ModelEnforcementDecision(
            effect_type="test.effect",
            determinism=EnumEffectDeterminism.UNKNOWN,
            source=None,
            mode=EnumEnforcementMode.PERMISSIVE,
            decision="allowed",
            reason="Test",
            timestamp=datetime.now(UTC),
        )

        entry = audit_trail.record(decision)
        assert entry is not None

    def test_implements_get_entries(self) -> None:
        """Test that ServiceAuditTrail implements get_entries()."""
        audit_trail = ServiceAuditTrail()
        entries = audit_trail.get_entries()
        assert isinstance(entries, list)

    def test_implements_get_summary(self) -> None:
        """Test that ServiceAuditTrail implements get_summary()."""
        audit_trail = ServiceAuditTrail()
        summary = audit_trail.get_summary()
        assert summary is not None

    def test_protocol_check_at_module_load(self) -> None:
        """Test that protocol compliance is verified at module load."""
        from omnibase_core.protocols.replay.protocol_audit_trail import (
            ProtocolAuditTrail,
        )

        audit_trail = ServiceAuditTrail()
        _check: ProtocolAuditTrail = audit_trail
        assert _check is not None
