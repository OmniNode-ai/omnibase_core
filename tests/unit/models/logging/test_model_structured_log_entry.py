# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelStructuredLogEntry canonical wire-format model.

Tests verify:
  - All required fields must be supplied; frozen; extra="forbid"
  - All enum fields are strongly typed (no raw strings)
  - UUID fields are UUID type, not raw str
  - artifact_refs and metadata have correct container types
  - Default factories generate valid values (entry_id, timestamp)
  - Round-trip via model_dump/model_validate is stable

No live infra required. All tests are @pytest.mark.unit.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_log_entry_status import EnumLogEntryStatus
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_redaction_state import EnumRedactionState
from omnibase_core.enums.enum_suppression_decision import EnumSuppressionDecision
from omnibase_core.models.logging.model_structured_log_entry import (
    ModelStructuredLogEntry,
)


def _make_minimal() -> ModelStructuredLogEntry:
    """Return the smallest valid ModelStructuredLogEntry."""
    return ModelStructuredLogEntry(
        source_system="test_node",
        operation="test_operation",
        level=EnumLogLevel.INFO,
        message="hello",
        status=EnumLogEntryStatus.EMITTED,
        redaction_state=EnumRedactionState.NONE,
        suppression_decision=EnumSuppressionDecision.EMIT,
    )


@pytest.mark.unit
class TestModelStructuredLogEntryConstruction:
    """Basic construction and field typing."""

    def test_minimal_construction_succeeds(self) -> None:
        entry = _make_minimal()
        assert entry.message == "hello"
        assert entry.source_system == "test_node"
        assert entry.operation == "test_operation"

    def test_entry_id_is_uuid(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.entry_id, UUID)

    def test_timestamp_is_datetime_utc(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.timestamp, datetime)
        assert entry.timestamp.tzinfo is not None
        # UTC timezone
        assert entry.timestamp.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_defaults_artifact_refs_empty_list(self) -> None:
        entry = _make_minimal()
        assert entry.artifact_refs == []

    def test_defaults_metadata_empty_dict(self) -> None:
        entry = _make_minimal()
        assert entry.metadata == {}

    def test_optional_uuid_fields_default_none(self) -> None:
        entry = _make_minimal()
        assert entry.node_id is None
        assert entry.correlation_id is None
        assert entry.session_id is None

    def test_explicit_uuid_fields(self) -> None:
        cid = uuid4()
        sid = uuid4()
        nid = uuid4()
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.DEBUG,
            message="m",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=EnumRedactionState.NONE,
            suppression_decision=EnumSuppressionDecision.EMIT,
            correlation_id=cid,
            session_id=sid,
            node_id=nid,
        )
        assert entry.correlation_id == cid
        assert entry.session_id == sid
        assert entry.node_id == nid

    def test_artifact_refs_list_of_strings(self) -> None:
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.INFO,
            message="m",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=EnumRedactionState.NONE,
            suppression_decision=EnumSuppressionDecision.EMIT,
            artifact_refs=["art-001", "art-002"],
        )
        assert entry.artifact_refs == ["art-001", "art-002"]

    def test_metadata_dict_of_strings(self) -> None:
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.WARNING,
            message="m",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=EnumRedactionState.NONE,
            suppression_decision=EnumSuppressionDecision.EMIT,
            metadata={"key": "value"},
        )
        assert entry.metadata == {"key": "value"}


@pytest.mark.unit
class TestModelStructuredLogEntryEnums:
    """Enum field typing tests."""

    def test_level_is_enum_log_level(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.level, EnumLogLevel)

    def test_status_is_enum_log_entry_status(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.status, EnumLogEntryStatus)

    def test_redaction_state_is_enum_redaction_state(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.redaction_state, EnumRedactionState)

    def test_suppression_decision_is_enum_suppression_decision(self) -> None:
        entry = _make_minimal()
        assert isinstance(entry.suppression_decision, EnumSuppressionDecision)

    @pytest.mark.parametrize("status", tuple(EnumLogEntryStatus.__members__.values()))
    def test_all_log_entry_status_values_accepted(
        self, status: EnumLogEntryStatus
    ) -> None:
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.INFO,
            message="m",
            status=status,
            redaction_state=EnumRedactionState.NONE,
            suppression_decision=EnumSuppressionDecision.EMIT,
        )
        assert entry.status == status

    @pytest.mark.parametrize("state", tuple(EnumRedactionState.__members__.values()))
    def test_all_redaction_state_values_accepted(
        self, state: EnumRedactionState
    ) -> None:
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.INFO,
            message="m",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=state,
            suppression_decision=EnumSuppressionDecision.EMIT,
        )
        assert entry.redaction_state == state

    @pytest.mark.parametrize(
        "decision", tuple(EnumSuppressionDecision.__members__.values())
    )
    def test_all_suppression_decision_values_accepted(
        self, decision: EnumSuppressionDecision
    ) -> None:
        entry = ModelStructuredLogEntry(
            source_system="n",
            operation="op",
            level=EnumLogLevel.INFO,
            message="m",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=EnumRedactionState.NONE,
            suppression_decision=decision,
        )
        assert entry.suppression_decision == decision


@pytest.mark.unit
class TestModelStructuredLogEntryFrozenAndExtra:
    """frozen=True and extra="forbid" enforcement."""

    def test_mutation_raises_validation_error(self) -> None:
        entry = _make_minimal()
        with pytest.raises(ValidationError):
            entry.message = "mutated"  # type: ignore[misc]

    def test_extra_field_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ModelStructuredLogEntry(
                source_system="n",
                operation="op",
                level=EnumLogLevel.INFO,
                message="m",
                status=EnumLogEntryStatus.EMITTED,
                redaction_state=EnumRedactionState.NONE,
                suppression_decision=EnumSuppressionDecision.EMIT,
                unexpected_field="boom",  # type: ignore[call-arg]
            )

    def test_missing_required_field_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ModelStructuredLogEntry(  # type: ignore[call-arg]
                source_system="n",
                # operation is missing
                level=EnumLogLevel.INFO,
                message="m",
                status=EnumLogEntryStatus.EMITTED,
                redaction_state=EnumRedactionState.NONE,
                suppression_decision=EnumSuppressionDecision.EMIT,
            )


@pytest.mark.unit
class TestModelStructuredLogEntryRoundTrip:
    """Serialization round-trip stability."""

    def test_model_dump_and_validate_round_trip(self) -> None:
        original = ModelStructuredLogEntry(
            source_system="node_builder",
            operation="build_loop",
            level=EnumLogLevel.ERROR,
            message="build failed",
            status=EnumLogEntryStatus.EMITTED,
            redaction_state=EnumRedactionState.PARTIAL,
            suppression_decision=EnumSuppressionDecision.EMIT,
            correlation_id=uuid4(),
            session_id=uuid4(),
            node_id=uuid4(),
            artifact_refs=["art-abc"],
            metadata={"phase": "compile"},
        )
        dumped = original.model_dump(mode="json")
        restored = ModelStructuredLogEntry.model_validate(dumped)
        assert restored == original

    def test_json_serialization_includes_all_fields(self) -> None:
        entry = _make_minimal()
        dumped = entry.model_dump(mode="json")
        expected_keys = {
            "entry_id",
            "timestamp",
            "source_system",
            "operation",
            "node_id",
            "correlation_id",
            "session_id",
            "level",
            "message",
            "status",
            "redaction_state",
            "suppression_decision",
            "artifact_refs",
            "metadata",
        }
        assert set(dumped.keys()) == expected_keys
