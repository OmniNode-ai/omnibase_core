# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for InjectorUUID - UUID injector for deterministic replay.

Tests cover:
- PASS_THROUGH mode generates real UUIDs
- RECORDING mode captures UUIDs
- REPLAYING mode returns recorded UUIDs in sequence
- Sequence exhaustion raises error
- reset() resets sequence
- uuid1() and uuid4() methods

OMN-1150: Replay Safety Enforcement

.. versionadded:: 0.6.3
"""

from __future__ import annotations

from uuid import UUID

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
from omnibase_core.errors import ModelOnexError
from omnibase_core.services.replay.injector_uuid import InjectorUUID

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def pass_through_injector() -> InjectorUUID:
    """Create a pass-through (production) mode UUID injector."""
    return InjectorUUID(mode=EnumRecorderMode.PASS_THROUGH)


@pytest.fixture
def recording_injector() -> InjectorUUID:
    """Create a recording mode UUID injector."""
    return InjectorUUID(mode=EnumRecorderMode.RECORDING)


@pytest.fixture
def sample_uuids() -> list[UUID]:
    """Create sample UUIDs for replay testing."""
    return [
        UUID("550e8400-e29b-41d4-a716-446655440001"),
        UUID("550e8400-e29b-41d4-a716-446655440002"),
        UUID("550e8400-e29b-41d4-a716-446655440003"),
    ]


@pytest.fixture
def replaying_injector(sample_uuids: list[UUID]) -> InjectorUUID:
    """Create a replaying mode UUID injector with pre-recorded UUIDs."""
    return InjectorUUID(mode=EnumRecorderMode.REPLAYING, recorded_uuids=sample_uuids)


# =============================================================================
# TEST PASS_THROUGH MODE
# =============================================================================


@pytest.mark.unit
class TestPassThroughMode:
    """Tests for PASS_THROUGH (production) mode."""

    def test_pass_through_generates_real_uuid4(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that PASS_THROUGH mode generates real UUID4."""
        uuid1 = pass_through_injector.uuid4()
        uuid2 = pass_through_injector.uuid4()

        assert isinstance(uuid1, UUID)
        assert isinstance(uuid2, UUID)
        assert uuid1.version == 4
        assert uuid2.version == 4
        # UUIDs should be different
        assert uuid1 != uuid2

    def test_pass_through_generates_real_uuid1(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that PASS_THROUGH mode generates real UUID1."""
        uuid1 = pass_through_injector.uuid1()
        uuid2 = pass_through_injector.uuid1()

        assert isinstance(uuid1, UUID)
        assert isinstance(uuid2, UUID)
        assert uuid1.version == 1
        assert uuid2.version == 1

    def test_pass_through_is_not_recording(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that PASS_THROUGH mode is not recording."""
        assert pass_through_injector.is_recording is False
        assert pass_through_injector.is_replaying is False

    def test_pass_through_does_not_record_uuids(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that PASS_THROUGH mode does not record UUIDs."""
        _ = pass_through_injector.uuid4()
        _ = pass_through_injector.uuid4()

        assert pass_through_injector.recorded_count == 0
        assert pass_through_injector.get_recorded() == []

    def test_pass_through_sequence_index_stays_zero(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that sequence index stays at 0 in PASS_THROUGH mode."""
        _ = pass_through_injector.uuid4()
        _ = pass_through_injector.uuid4()

        assert pass_through_injector.sequence_index == 0

    def test_pass_through_reset_is_noop(
        self, pass_through_injector: InjectorUUID
    ) -> None:
        """Test that reset is a no-op in PASS_THROUGH mode."""
        _ = pass_through_injector.uuid4()
        pass_through_injector.reset()

        assert pass_through_injector.sequence_index == 0
        assert pass_through_injector.recorded_count == 0


# =============================================================================
# TEST RECORDING MODE
# =============================================================================


@pytest.mark.unit
class TestRecordingMode:
    """Tests for RECORDING mode."""

    def test_recording_mode_captures_uuids(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that RECORDING mode captures generated UUIDs."""
        uuid1 = recording_injector.uuid4()
        uuid2 = recording_injector.uuid4()

        recorded = recording_injector.get_recorded()
        assert len(recorded) == 2
        assert uuid1 in recorded
        assert uuid2 in recorded

    def test_recording_mode_captures_uuid1(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that RECORDING mode captures UUID1."""
        uuid1 = recording_injector.uuid1()

        recorded = recording_injector.get_recorded()
        assert len(recorded) == 1
        assert uuid1 in recorded

    def test_recording_mode_is_recording(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that RECORDING mode is_recording returns True."""
        assert recording_injector.is_recording is True
        assert recording_injector.is_replaying is False

    def test_recording_mode_preserves_order(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that RECORDING mode preserves UUID order."""
        uuids = [recording_injector.uuid4() for _ in range(5)]

        recorded = recording_injector.get_recorded()
        assert recorded == uuids

    def test_recording_mode_recorded_count(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test recorded_count property."""
        assert recording_injector.recorded_count == 0

        _ = recording_injector.uuid4()
        assert recording_injector.recorded_count == 1

        _ = recording_injector.uuid4()
        assert recording_injector.recorded_count == 2

    def test_recording_mode_get_recorded_returns_copy(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that get_recorded returns a copy."""
        _ = recording_injector.uuid4()
        recorded1 = recording_injector.get_recorded()
        recorded2 = recording_injector.get_recorded()

        assert recorded1 == recorded2
        assert recorded1 is not recorded2

    def test_recording_mode_reset_clears_recorded(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that reset clears recorded UUIDs in RECORDING mode."""
        _ = recording_injector.uuid4()
        _ = recording_injector.uuid4()
        assert recording_injector.recorded_count == 2

        recording_injector.reset()

        assert recording_injector.recorded_count == 0
        assert recording_injector.get_recorded() == []

    def test_recording_mode_sequence_index_stays_zero(
        self, recording_injector: InjectorUUID
    ) -> None:
        """Test that sequence index stays at 0 in RECORDING mode."""
        _ = recording_injector.uuid4()
        _ = recording_injector.uuid4()

        assert recording_injector.sequence_index == 0


# =============================================================================
# TEST REPLAYING MODE
# =============================================================================


@pytest.mark.unit
class TestReplayingMode:
    """Tests for REPLAYING mode."""

    def test_replaying_mode_returns_recorded_uuids(
        self, replaying_injector: InjectorUUID, sample_uuids: list[UUID]
    ) -> None:
        """Test that REPLAYING mode returns pre-recorded UUIDs."""
        result1 = replaying_injector.uuid4()
        result2 = replaying_injector.uuid4()
        result3 = replaying_injector.uuid4()

        assert result1 == sample_uuids[0]
        assert result2 == sample_uuids[1]
        assert result3 == sample_uuids[2]

    def test_replaying_mode_returns_in_sequence(
        self, replaying_injector: InjectorUUID, sample_uuids: list[UUID]
    ) -> None:
        """Test that REPLAYING mode returns UUIDs in sequence."""
        for i, expected in enumerate(sample_uuids):
            result = replaying_injector.uuid4()
            assert result == expected

    def test_replaying_mode_is_replaying(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that REPLAYING mode is_replaying returns True."""
        assert replaying_injector.is_replaying is True
        assert replaying_injector.is_recording is False

    def test_replaying_mode_advances_sequence_index(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that REPLAYING mode advances sequence index."""
        assert replaying_injector.sequence_index == 0

        _ = replaying_injector.uuid4()
        assert replaying_injector.sequence_index == 1

        _ = replaying_injector.uuid4()
        assert replaying_injector.sequence_index == 2

    def test_replaying_mode_uuid1_uses_same_sequence(
        self, replaying_injector: InjectorUUID, sample_uuids: list[UUID]
    ) -> None:
        """Test that uuid1() uses the same sequence as uuid4()."""
        result1 = replaying_injector.uuid1()
        result2 = replaying_injector.uuid4()

        assert result1 == sample_uuids[0]
        assert result2 == sample_uuids[1]

    def test_replaying_mode_reset_restarts_sequence(
        self, replaying_injector: InjectorUUID, sample_uuids: list[UUID]
    ) -> None:
        """Test that reset() restarts the replay sequence."""
        # Consume some UUIDs
        _ = replaying_injector.uuid4()
        _ = replaying_injector.uuid4()
        assert replaying_injector.sequence_index == 2

        # Reset
        replaying_injector.reset()
        assert replaying_injector.sequence_index == 0

        # Should replay from beginning
        result = replaying_injector.uuid4()
        assert result == sample_uuids[0]


# =============================================================================
# TEST SEQUENCE EXHAUSTION
# =============================================================================


@pytest.mark.unit
class TestSequenceExhaustion:
    """Tests for sequence exhaustion error handling."""

    def test_exhausted_sequence_raises_error(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that exhausted sequence raises ModelOnexError."""
        # Consume all 3 UUIDs
        _ = replaying_injector.uuid4()
        _ = replaying_injector.uuid4()
        _ = replaying_injector.uuid4()

        # Should raise error on next call
        with pytest.raises(ModelOnexError) as exc_info:
            replaying_injector.uuid4()

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED

    def test_exhausted_sequence_error_message(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that exhausted sequence error has descriptive message."""
        # Consume all UUIDs
        for _ in range(3):
            replaying_injector.uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            replaying_injector.uuid4()

        error_msg = str(exc_info.value.message).lower()
        assert "exhausted" in error_msg
        assert "3" in str(exc_info.value.message)  # recorded count

    def test_exhausted_sequence_uuid1_raises_error(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that uuid1() also raises error when sequence exhausted."""
        for _ in range(3):
            replaying_injector.uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            replaying_injector.uuid1()

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED

    def test_empty_recorded_list_raises_immediately(self) -> None:
        """Test that empty recorded list raises on first call."""
        injector = InjectorUUID(mode=EnumRecorderMode.REPLAYING, recorded_uuids=[])

        with pytest.raises(ModelOnexError) as exc_info:
            injector.uuid4()

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED

    def test_exhausted_sequence_error_has_helpful_context(
        self, replaying_injector: InjectorUUID
    ) -> None:
        """Test that exhausted sequence error includes helpful debug context."""
        # Consume all 3 UUIDs
        for _ in range(3):
            replaying_injector.uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            replaying_injector.uuid4()

        error = exc_info.value
        # Context is stored in error.model.context
        ctx = error.model.context
        assert "sequence_index" in ctx
        assert ctx["sequence_index"] == 3  # 0-indexed, so asking for 4th
        assert "recorded_count" in ctx
        assert ctx["recorded_count"] == 3
        assert "recorded_uuids_preview" in ctx
        # Preview should contain the recorded UUIDs as strings
        assert isinstance(ctx["recorded_uuids_preview"], list)
        assert len(ctx["recorded_uuids_preview"]) == 3
        assert "hint" in ctx
        assert "RECORDING" in ctx["hint"]

        # Message should have actionable guidance
        error_msg = str(error.model.message)
        assert "code path" in error_msg.lower()
        assert "re-record" in error_msg.lower() or "recording" in error_msg.lower()


# =============================================================================
# TEST INVARIANTS
# =============================================================================


@pytest.mark.unit
class TestRecordReplayInvariant:
    """Tests for recording + replay invariant (determinism)."""

    def test_record_then_replay_produces_same_uuids(self) -> None:
        """Test that recording then replaying produces identical UUIDs."""
        # Record phase
        recorder = InjectorUUID(mode=EnumRecorderMode.RECORDING)
        recorded_uuids = [recorder.uuid4() for _ in range(5)]
        captured = recorder.get_recorded()

        # Replay phase
        replayer = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING, recorded_uuids=captured
        )
        replayed_uuids = [replayer.uuid4() for _ in range(5)]

        assert recorded_uuids == replayed_uuids

    def test_record_then_replay_with_uuid1(self) -> None:
        """Test recording and replaying uuid1() calls."""
        # Record
        recorder = InjectorUUID(mode=EnumRecorderMode.RECORDING)
        recorded_uuid1 = recorder.uuid1()
        recorded_uuid4 = recorder.uuid4()
        captured = recorder.get_recorded()

        # Replay
        replayer = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING, recorded_uuids=captured
        )
        replayed_uuid1 = replayer.uuid1()
        replayed_uuid4 = replayer.uuid4()

        assert recorded_uuid1 == replayed_uuid1
        assert recorded_uuid4 == replayed_uuid4


# =============================================================================
# TEST EDGE CASES
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_default_mode_is_pass_through(self) -> None:
        """Test that default mode is PASS_THROUGH."""
        injector = InjectorUUID()

        assert injector.is_recording is False
        assert injector.is_replaying is False

    def test_none_recorded_uuids_treated_as_empty(self) -> None:
        """Test that None recorded_uuids is treated as empty list."""
        injector = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING,
            recorded_uuids=None,  # type: ignore[arg-type]
        )

        with pytest.raises(ModelOnexError):
            injector.uuid4()

    def test_recorded_uuids_are_copied(self) -> None:
        """Test that recorded_uuids list is copied, not referenced."""
        original_list = [UUID("550e8400-e29b-41d4-a716-446655440001")]
        injector = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING, recorded_uuids=original_list
        )

        # Modify original list
        original_list.append(UUID("550e8400-e29b-41d4-a716-446655440002"))

        # Injector should not be affected
        _ = injector.uuid4()
        with pytest.raises(ModelOnexError):
            injector.uuid4()  # Should only have 1 UUID

    def test_multiple_resets_allowed(
        self, replaying_injector: InjectorUUID, sample_uuids: list[UUID]
    ) -> None:
        """Test that multiple resets work correctly."""
        # First pass
        _ = replaying_injector.uuid4()
        replaying_injector.reset()

        # Second pass
        _ = replaying_injector.uuid4()
        _ = replaying_injector.uuid4()
        replaying_injector.reset()

        # Third pass - should work
        result = replaying_injector.uuid4()
        assert result == sample_uuids[0]

    def test_single_uuid_replay(self) -> None:
        """Test replaying a single UUID."""
        single_uuid = UUID("550e8400-e29b-41d4-a716-446655440001")
        injector = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING, recorded_uuids=[single_uuid]
        )

        result = injector.uuid4()
        assert result == single_uuid

        with pytest.raises(ModelOnexError):
            injector.uuid4()


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestProtocolCompliance:
    """Tests for ProtocolUUIDService compliance."""

    def test_implements_uuid4(self) -> None:
        """Test that InjectorUUID implements uuid4()."""
        injector = InjectorUUID()
        result = injector.uuid4()
        assert isinstance(result, UUID)

    def test_implements_uuid1(self) -> None:
        """Test that InjectorUUID implements uuid1()."""
        injector = InjectorUUID()
        result = injector.uuid1()
        assert isinstance(result, UUID)

    def test_protocol_check_at_module_load(self) -> None:
        """Test that protocol compliance is checked at module load."""
        # This is verified by the module-level check:
        # _uuid_check: ProtocolUUIDService = InjectorUUID()
        from omnibase_core.protocols.replay.protocol_uuid_service import (
            ProtocolUUIDService,
        )

        injector = InjectorUUID()
        # Duck typing check
        assert hasattr(injector, "uuid4")
        assert hasattr(injector, "uuid1")
        assert callable(injector.uuid4)
        assert callable(injector.uuid1)

        # Structural subtyping check
        _check: ProtocolUUIDService = injector
        assert _check is not None
