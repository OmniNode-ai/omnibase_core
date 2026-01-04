# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for RecorderEffect - Effect Recorder for Replay Infrastructure.

Tests cover:
- Pass-through mode (production): no recording, no modification
- Recording mode: captures effect intents and results
- Replaying mode: returns pre-recorded results
- Sequence index tracking for execution order
- Immutability of recorded effects
- Protocol compliance (ProtocolEffectRecorder)
- Thread safety considerations
- Error recording capabilities
- Intent matching for replay

This test file follows TDD - tests are written BEFORE implementation.

.. versionadded:: 0.4.0
    Added as part of Replay Infrastructure (OMN-1116)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
    from omnibase_core.pipeline.replay.recorder_effect import (
        RecorderEffect,
    )
    from omnibase_core.protocols.replay.protocol_time_service import ProtocolTimeService


@pytest.fixture
def fixed_time() -> datetime:
    """Create a fixed datetime for testing."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)


@pytest.fixture
def mock_time_service(fixed_time: datetime) -> ProtocolTimeService:
    """Create a mock time service that returns fixed time."""
    from omnibase_core.pipeline.replay.injector_time import InjectorTime

    return InjectorTime(fixed_time=fixed_time)


@pytest.fixture
def sample_intent() -> dict[str, Any]:
    """Create sample intent data."""
    return {
        "url": "https://api.example.com/users",
        "method": "GET",
        "params": {"page": 1},
    }


@pytest.fixture
def sample_result() -> dict[str, Any]:
    """Create sample result data."""
    return {
        "status_code": 200,
        "body": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    }


@pytest.fixture
def pass_through_recorder() -> RecorderEffect:
    """Create a recorder in pass-through mode."""
    from omnibase_core.enums.replay import EnumRecorderMode
    from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect

    return RecorderEffect(mode=EnumRecorderMode.PASS_THROUGH)


@pytest.fixture
def recording_recorder(
    mock_time_service: ProtocolTimeService,
) -> RecorderEffect:
    """Create a recorder in recording mode."""
    from omnibase_core.enums.replay import EnumRecorderMode
    from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect

    return RecorderEffect(
        mode=EnumRecorderMode.RECORDING,
        time_service=mock_time_service,
    )


@pytest.fixture
def sample_records(fixed_time: datetime) -> list[ModelEffectRecord]:
    """Create sample pre-recorded records for replay."""
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

    return [
        ModelEffectRecord(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users", "method": "GET"},
            result={"status_code": 200, "body": [{"id": 1}]},
            captured_at=fixed_time,
            sequence_index=0,
        ),
        ModelEffectRecord(
            effect_type="db.query",
            intent={"table": "users", "query": "SELECT * FROM users"},
            result={"rows": [{"id": 1, "name": "Alice"}]},
            captured_at=fixed_time,
            sequence_index=1,
        ),
    ]


@pytest.fixture
def replay_recorder(sample_records: list[ModelEffectRecord]) -> RecorderEffect:
    """Create a recorder in replay mode with pre-recorded data."""
    from omnibase_core.enums.replay import EnumRecorderMode
    from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect

    return RecorderEffect(
        mode=EnumRecorderMode.REPLAYING,
        records=sample_records,
    )


@pytest.mark.unit
class TestRecorderEffectPassThroughMode:
    """Test RecorderEffect in pass-through mode (production)."""

    def test_pass_through_mode_does_not_record(
        self,
        pass_through_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that pass-through mode does not store records."""
        # Try to record in pass-through mode
        pass_through_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )

        # Should not have recorded anything
        assert len(pass_through_recorder.get_all_records()) == 0

    def test_is_recording_false_in_pass_through(
        self, pass_through_recorder: RecorderEffect
    ) -> None:
        """Test that is_recording is False in pass-through mode."""
        assert pass_through_recorder.is_recording is False

    def test_is_replaying_false_in_pass_through(
        self, pass_through_recorder: RecorderEffect
    ) -> None:
        """Test that is_replaying is False in pass-through mode."""
        assert pass_through_recorder.is_replaying is False

    def test_get_replay_result_returns_none_in_pass_through(
        self,
        pass_through_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
    ) -> None:
        """Test that get_replay_result returns None in pass-through mode."""
        result = pass_through_recorder.get_replay_result(
            effect_type="http.get",
            intent=sample_intent,
        )
        assert result is None


@pytest.mark.unit
class TestRecorderEffectRecordingMode:
    """Test RecorderEffect in recording mode."""

    def test_recording_mode_captures_effects(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that recording mode captures effect intents and results."""
        record = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )

        assert record is not None
        assert record.effect_type == "http.get"
        assert record.intent == sample_intent
        assert record.result == sample_result

    def test_is_recording_true_in_recording_mode(
        self, recording_recorder: RecorderEffect
    ) -> None:
        """Test that is_recording is True in recording mode."""
        assert recording_recorder.is_recording is True

    def test_is_replaying_false_in_recording_mode(
        self, recording_recorder: RecorderEffect
    ) -> None:
        """Test that is_replaying is False in recording mode."""
        assert recording_recorder.is_replaying is False

    def test_sequence_index_increments(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that sequence_index increments for each recorded effect."""
        record1 = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )
        record2 = recording_recorder.record(
            effect_type="db.query",
            intent={"query": "SELECT 1"},
            result={"rows": []},
        )
        record3 = recording_recorder.record(
            effect_type="file.read",
            intent={"path": "/tmp/file.txt"},
            result={"content": "hello"},
        )

        assert record1.sequence_index == 0
        assert record2.sequence_index == 1
        assert record3.sequence_index == 2

    def test_captured_at_uses_time_service(
        self,
        recording_recorder: RecorderEffect,
        fixed_time: datetime,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that captured_at timestamp uses the injected time service."""
        record = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )

        assert record.captured_at == fixed_time

    def test_get_all_records_returns_all_recorded(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that get_all_records returns all recorded effects."""
        recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )
        recording_recorder.record(
            effect_type="db.query",
            intent={"query": "SELECT 1"},
            result={"rows": []},
        )

        records = recording_recorder.get_all_records()
        assert len(records) == 2
        assert records[0].effect_type == "http.get"
        assert records[1].effect_type == "db.query"


@pytest.mark.unit
class TestRecorderEffectReplayingMode:
    """Test RecorderEffect in replaying mode."""

    def test_replaying_mode_returns_recorded_results(
        self, replay_recorder: RecorderEffect
    ) -> None:
        """Test that replaying mode returns pre-recorded results."""
        result = replay_recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users", "method": "GET"},
        )

        assert result is not None
        assert result["status_code"] == 200

    def test_is_replaying_true_in_replay_mode(
        self, replay_recorder: RecorderEffect
    ) -> None:
        """Test that is_replaying is True in replay mode."""
        assert replay_recorder.is_replaying is True

    def test_is_recording_false_in_replay_mode(
        self, replay_recorder: RecorderEffect
    ) -> None:
        """Test that is_recording is False in replay mode."""
        assert replay_recorder.is_recording is False

    def test_replay_matches_recording_order(
        self, replay_recorder: RecorderEffect
    ) -> None:
        """Test that replay returns results in sequence order."""
        # First call should return first record's result
        result1 = replay_recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users", "method": "GET"},
        )
        # Second call should return second record's result
        result2 = replay_recorder.get_replay_result(
            effect_type="db.query",
            intent={"table": "users", "query": "SELECT * FROM users"},
        )

        assert result1 is not None
        assert result1["status_code"] == 200

        assert result2 is not None
        assert "rows" in result2

    def test_replay_returns_none_for_unmatched_effect(
        self, replay_recorder: RecorderEffect
    ) -> None:
        """Test that replay returns None for effects not in recording."""
        result = replay_recorder.get_replay_result(
            effect_type="unknown.effect",
            intent={"some": "data"},
        )
        assert result is None


@pytest.mark.unit
class TestRecorderEffectImmutability:
    """Test RecorderEffect record immutability."""

    def test_records_are_immutable(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that recorded records are immutable (frozen)."""
        from pydantic import ValidationError

        record = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )

        # Attempt to modify should raise
        with pytest.raises(ValidationError):
            record.effect_type = "modified"

    def test_get_all_records_returns_copy(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
        sample_result: dict[str, Any],
    ) -> None:
        """Test that get_all_records returns a copy, not internal list."""
        recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result=sample_result,
        )

        records = recording_recorder.get_all_records()
        original_len = len(records)

        # Modify the returned list
        records.clear()

        # Internal list should be unchanged
        assert len(recording_recorder.get_all_records()) == original_len


@pytest.mark.unit
class TestRecorderEffectProtocolCompliance:
    """Test that RecorderEffect implements ProtocolEffectRecorder correctly."""

    def test_implements_protocol(self) -> None:
        """Test that RecorderEffect implements ProtocolEffectRecorder."""
        from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect
        from omnibase_core.protocols.replay.protocol_effect_recorder import (
            ProtocolEffectRecorder,
        )

        recorder = RecorderEffect()

        # Protocol compliance check
        assert isinstance(recorder, ProtocolEffectRecorder)

    def test_has_required_methods(self, pass_through_recorder: RecorderEffect) -> None:
        """Test that RecorderEffect has all required protocol methods."""
        assert hasattr(pass_through_recorder, "is_recording")
        assert hasattr(pass_through_recorder, "is_replaying")
        assert hasattr(pass_through_recorder, "record")
        assert callable(pass_through_recorder.record)
        assert hasattr(pass_through_recorder, "get_replay_result")
        assert callable(pass_through_recorder.get_replay_result)
        assert hasattr(pass_through_recorder, "get_all_records")
        assert callable(pass_through_recorder.get_all_records)


@pytest.mark.unit
class TestRecorderEffectErrorRecording:
    """Test RecorderEffect error recording capabilities."""

    def test_error_recording(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
    ) -> None:
        """Test that failed effects can be recorded."""
        record = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result={},
            success=False,
            error_message="Connection timeout after 30s",
        )

        assert record.success is False
        assert record.error_message == "Connection timeout after 30s"

    def test_error_record_preserves_intent(
        self,
        recording_recorder: RecorderEffect,
        sample_intent: dict[str, Any],
    ) -> None:
        """Test that error records preserve the original intent."""
        record = recording_recorder.record(
            effect_type="http.get",
            intent=sample_intent,
            result={},
            success=False,
            error_message="Failed",
        )

        assert record.intent == sample_intent


@pytest.mark.unit
class TestRecorderEffectIntentMatching:
    """Test effect intent matching for replay."""

    def test_intent_matching_for_replay(self, fixed_time: datetime) -> None:
        """Test that replay correctly matches intents."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
        from omnibase_core.pipeline.replay.recorder_effect import (
            EnumRecorderMode,
            RecorderEffect,
        )

        records = [
            ModelEffectRecord(
                effect_type="http.get",
                intent={"url": "https://api1.com", "method": "GET"},
                result={"response": "api1"},
                captured_at=fixed_time,
                sequence_index=0,
            ),
            ModelEffectRecord(
                effect_type="http.get",
                intent={"url": "https://api2.com", "method": "GET"},
                result={"response": "api2"},
                captured_at=fixed_time,
                sequence_index=1,
            ),
        ]

        recorder = RecorderEffect(
            mode=EnumRecorderMode.REPLAYING,
            records=records,
        )

        # Should match second record by intent
        result = recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api2.com", "method": "GET"},
        )

        assert result is not None
        assert result["response"] == "api2"

    def test_intent_matching_is_exact(self, fixed_time: datetime) -> None:
        """Test that intent matching is exact (not partial)."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
        from omnibase_core.pipeline.replay.recorder_effect import (
            EnumRecorderMode,
            RecorderEffect,
        )

        records = [
            ModelEffectRecord(
                effect_type="http.get",
                intent={"url": "https://api.com", "method": "GET", "params": {"a": 1}},
                result={"matched": True},
                captured_at=fixed_time,
                sequence_index=0,
            ),
        ]

        recorder = RecorderEffect(
            mode=EnumRecorderMode.REPLAYING,
            records=records,
        )

        # Partial match should not work
        result = recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.com", "method": "GET"},  # Missing params
        )

        assert result is None


@pytest.mark.unit
class TestRecorderEffectModeEnum:
    """Test EnumRecorderMode enum values."""

    def test_mode_enum_values(self) -> None:
        """Test that EnumRecorderMode has expected values."""
        from omnibase_core.enums.replay import EnumRecorderMode

        assert EnumRecorderMode.PASS_THROUGH.value == "pass_through"
        assert EnumRecorderMode.RECORDING.value == "recording"
        assert EnumRecorderMode.REPLAYING.value == "replaying"

    def test_default_mode_is_pass_through(self) -> None:
        """Test that default mode is PASS_THROUGH."""
        from omnibase_core.pipeline.replay.recorder_effect import RecorderEffect

        recorder = RecorderEffect()
        assert recorder.is_recording is False
        assert recorder.is_replaying is False
