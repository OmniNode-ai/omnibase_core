# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ExecutorReplay - Replay Executor for Replay Infrastructure.

Tests cover:
- Production session creation
- Recording session creation (with optional seed)
- Replay session creation from recorded data
- Manifest capture (JSON-serializable)
- Sync and async function execution
- Time determinism across recording and replay
- RNG determinism across recording and replay
- Effect stubbing during replay
- Full record-then-replay cycle
- Session mode properties

This test file follows TDD - tests are written BEFORE implementation.

.. versionadded:: 0.4.0
    Added as part of Replay Infrastructure (OMN-1116)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay
    from omnibase_core.pipeline.replay.runner_replay_session import ReplaySession


@pytest.fixture
def fixed_time() -> datetime:
    """Create a fixed datetime for testing."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)


@pytest.fixture
def executor() -> ExecutorReplay:
    """Create an ExecutorReplay instance."""
    from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay

    return ExecutorReplay()


@pytest.fixture
def sample_effect_records(fixed_time: datetime) -> list[dict[str, Any]]:
    """Create sample effect records for replay."""
    from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

    records = [
        ModelEffectRecord(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users"},
            result={"status_code": 200, "body": [{"id": 1}]},
            captured_at=fixed_time,
            sequence_index=0,
        ),
        ModelEffectRecord(
            effect_type="db.query",
            intent={"query": "SELECT * FROM users"},
            result={"rows": [{"id": 1, "name": "Alice"}]},
            captured_at=fixed_time,
            sequence_index=1,
        ),
    ]
    return records


@pytest.mark.unit
class TestExecutorReplayProductionSession:
    """Test ExecutorReplay production session creation."""

    def test_create_production_session(self, executor: ExecutorReplay) -> None:
        """Test production session has correct mode and services."""
        from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode

        session = executor.create_production_session()

        assert session.mode == EnumReplayMode.PRODUCTION
        assert session.time_service is not None
        assert session.rng_service is not None
        assert session.effect_recorder is not None

    def test_production_session_time_is_current(self, executor: ExecutorReplay) -> None:
        """Test production session uses current time (not frozen)."""
        session = executor.create_production_session()

        # Time should be close to now (within a second)
        now = datetime.now(UTC)
        session_time = session.time_service.now()

        time_diff = abs((session_time - now).total_seconds())
        assert time_diff < 1.0

    def test_production_session_effect_recorder_is_pass_through(
        self, executor: ExecutorReplay
    ) -> None:
        """Test production session effect recorder is in pass-through mode."""
        session = executor.create_production_session()

        assert session.effect_recorder.is_recording is False
        assert session.effect_recorder.is_replaying is False


@pytest.mark.unit
class TestExecutorReplayRecordingSession:
    """Test ExecutorReplay recording session creation."""

    def test_create_recording_session(self, executor: ExecutorReplay) -> None:
        """Test recording session has correct mode and services."""
        from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode

        session = executor.create_recording_session()

        assert session.mode == EnumReplayMode.RECORDING
        assert session.time_service is not None
        assert session.rng_service is not None
        assert session.effect_recorder is not None

    def test_create_recording_session_with_seed(self, executor: ExecutorReplay) -> None:
        """Test recording session with custom RNG seed."""
        seed = 42
        session = executor.create_recording_session(rng_seed=seed)

        assert session.rng_service.seed == seed

    def test_recording_session_auto_generates_seed(
        self, executor: ExecutorReplay
    ) -> None:
        """Test recording session auto-generates seed if not provided."""
        session = executor.create_recording_session()

        # Seed should be set (auto-generated)
        assert session.rng_service.seed is not None
        assert isinstance(session.rng_service.seed, int)

    def test_recording_session_effect_recorder_is_recording(
        self, executor: ExecutorReplay
    ) -> None:
        """Test recording session effect recorder is in recording mode."""
        session = executor.create_recording_session()

        assert session.effect_recorder.is_recording is True
        assert session.effect_recorder.is_replaying is False

    def test_recording_session_stores_seed_in_context(
        self, executor: ExecutorReplay
    ) -> None:
        """Test that recording session stores RNG seed in context."""
        seed = 12345
        session = executor.create_recording_session(rng_seed=seed)

        assert session.context.rng_seed == seed


@pytest.mark.unit
class TestExecutorReplayReplaySession:
    """Test ExecutorReplay replay session creation."""

    def test_create_replay_session(
        self,
        executor: ExecutorReplay,
        fixed_time: datetime,
        sample_effect_records: list,
    ) -> None:
        """Test replay session has correct mode and services."""
        from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode

        session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=sample_effect_records,
        )

        assert session.mode == EnumReplayMode.REPLAYING
        assert session.time_service is not None
        assert session.rng_service is not None
        assert session.effect_recorder is not None

    def test_replay_session_uses_frozen_time(
        self,
        executor: ExecutorReplay,
        fixed_time: datetime,
        sample_effect_records: list,
    ) -> None:
        """Test replay session uses frozen time."""
        session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=sample_effect_records,
        )

        assert session.time_service.now() == fixed_time
        # Multiple calls should return same time
        assert session.time_service.now() == fixed_time

    def test_replay_session_uses_seeded_rng(
        self,
        executor: ExecutorReplay,
        fixed_time: datetime,
        sample_effect_records: list,
    ) -> None:
        """Test replay session uses seeded RNG."""
        session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=sample_effect_records,
        )

        assert session.rng_service.seed == 42

    def test_replay_session_effect_recorder_is_replaying(
        self,
        executor: ExecutorReplay,
        fixed_time: datetime,
        sample_effect_records: list,
    ) -> None:
        """Test replay session effect recorder is in replaying mode."""
        session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=sample_effect_records,
        )

        assert session.effect_recorder.is_replaying is True
        assert session.effect_recorder.is_recording is False

    def test_replay_session_stores_original_execution_id(
        self,
        executor: ExecutorReplay,
        fixed_time: datetime,
        sample_effect_records: list,
    ) -> None:
        """Test replay session stores original execution ID."""
        original_id = uuid4()
        session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=sample_effect_records,
            original_execution_id=original_id,
        )

        assert session.context.original_execution_id == original_id


@pytest.mark.unit
class TestExecutorReplayManifestCapture:
    """Test ExecutorReplay manifest capture."""

    def test_capture_manifest_includes_all_data(self, executor: ExecutorReplay) -> None:
        """Test manifest capture includes all required data."""
        session = executor.create_recording_session(rng_seed=42)

        # Simulate some recorded effects
        session.effect_recorder.record(
            effect_type="http.get",
            intent={"url": "https://api.example.com"},
            result={"status": 200},
        )

        manifest = executor.capture_manifest(session)

        # Check required fields
        assert "session_id" in manifest
        assert "time_frozen_at" in manifest
        assert "rng_seed" in manifest
        assert "effect_records" in manifest

        # Check values
        assert manifest["rng_seed"] == 42
        assert len(manifest["effect_records"]) == 1

    def test_manifest_serialization(self, executor: ExecutorReplay) -> None:
        """Test manifest is JSON-serializable."""
        import json

        session = executor.create_recording_session(rng_seed=42)
        session.effect_recorder.record(
            effect_type="test.effect",
            intent={"key": "value"},
            result={"data": 123},
        )

        manifest = executor.capture_manifest(session)

        # Should be JSON serializable without errors
        json_str = json.dumps(manifest)
        assert json_str is not None

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["rng_seed"] == 42

    def test_manifest_time_is_iso_format(self, executor: ExecutorReplay) -> None:
        """Test manifest time is in ISO format."""
        session = executor.create_recording_session()
        manifest = executor.capture_manifest(session)

        # Should be parseable as ISO datetime
        datetime.fromisoformat(manifest["time_frozen_at"])


@pytest.mark.unit
class TestExecutorReplaySyncExecution:
    """Test ExecutorReplay sync function execution."""

    def test_execute_sync_basic(self, executor: ExecutorReplay) -> None:
        """Test basic sync function execution."""
        session = executor.create_production_session()

        def add(a: int, b: int) -> int:
            return a + b

        result = executor.execute_sync(session, add, 2, 3)
        assert result == 5

    def test_execute_sync_with_kwargs(self, executor: ExecutorReplay) -> None:
        """Test sync execution with keyword arguments."""
        session = executor.create_production_session()

        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result = executor.execute_sync(session, greet, "World", greeting="Hi")
        assert result == "Hi, World!"

    def test_execute_sync_injects_session(self, executor: ExecutorReplay) -> None:
        """Test sync execution can inject session into function."""
        session = executor.create_recording_session(rng_seed=42)

        def get_random_value(replay_session: ReplaySession) -> float:
            return replay_session.rng_service.random()

        result = executor.execute_sync(session, get_random_value)
        assert isinstance(result, float)
        assert 0.0 <= result < 1.0


@pytest.mark.unit
class TestExecutorReplayAsyncExecution:
    """Test ExecutorReplay async function execution."""

    @pytest.mark.asyncio
    async def test_execute_async_basic(self, executor: ExecutorReplay) -> None:
        """Test basic async function execution."""
        session = executor.create_production_session()

        async def async_add(a: int, b: int) -> int:
            return a + b

        result = await executor.execute_async(session, async_add, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_execute_async_with_kwargs(self, executor: ExecutorReplay) -> None:
        """Test async execution with keyword arguments."""
        session = executor.create_production_session()

        async def async_greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result = await executor.execute_async(
            session, async_greet, "World", greeting="Hi"
        )
        assert result == "Hi, World!"

    @pytest.mark.asyncio
    async def test_execute_async_injects_session(
        self, executor: ExecutorReplay
    ) -> None:
        """Test async execution can inject session into function."""
        session = executor.create_recording_session(rng_seed=42)

        async def get_time(replay_session: ReplaySession) -> datetime:
            return replay_session.time_service.now()

        result = await executor.execute_async(session, get_time)
        assert isinstance(result, datetime)


@pytest.mark.unit
class TestExecutorReplayTimeDeterminism:
    """Test time determinism across recording and replay."""

    def test_replay_produces_same_time(
        self, executor: ExecutorReplay, fixed_time: datetime
    ) -> None:
        """Test replay produces same time as recorded."""
        # Create recording session
        recording_session = executor.create_recording_session()

        # Get recorded time
        recorded_time = recording_session.time_service.now()

        # Create replay session with that time
        replay_session = executor.create_replay_session(
            time_frozen_at=recorded_time,
            rng_seed=42,
            effect_records=[],
        )

        # Replay should return same time
        replayed_time = replay_session.time_service.now()
        assert replayed_time == recorded_time

    def test_time_frozen_across_multiple_calls(
        self, executor: ExecutorReplay, fixed_time: datetime
    ) -> None:
        """Test time remains frozen across multiple calls in replay."""
        replay_session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=[],
        )

        time1 = replay_session.time_service.now()
        time2 = replay_session.time_service.now()
        time3 = replay_session.time_service.now()

        assert time1 == time2 == time3 == fixed_time


@pytest.mark.unit
class TestExecutorReplayRNGDeterminism:
    """Test RNG determinism across recording and replay."""

    def test_replay_produces_same_rng_sequence(self, executor: ExecutorReplay) -> None:
        """Test replay produces same RNG sequence as recording."""
        seed = 42

        # Create recording session with known seed
        recording_session = executor.create_recording_session(rng_seed=seed)
        recorded_values = [recording_session.rng_service.random() for _ in range(5)]

        # Create replay session with same seed
        replay_session = executor.create_replay_session(
            time_frozen_at=datetime.now(UTC),
            rng_seed=seed,
            effect_records=[],
        )
        replayed_values = [replay_session.rng_service.random() for _ in range(5)]

        # Sequences should match
        assert recorded_values == replayed_values

    def test_different_seeds_produce_different_sequences(
        self, executor: ExecutorReplay
    ) -> None:
        """Test different seeds produce different sequences."""
        session1 = executor.create_recording_session(rng_seed=1)
        session2 = executor.create_recording_session(rng_seed=2)

        values1 = [session1.rng_service.random() for _ in range(5)]
        values2 = [session2.rng_service.random() for _ in range(5)]

        assert values1 != values2


@pytest.mark.unit
class TestExecutorReplayEffectStubbing:
    """Test effect stubbing during replay."""

    def test_replay_returns_recorded_effects(
        self, executor: ExecutorReplay, fixed_time: datetime
    ) -> None:
        """Test replay returns recorded effect results."""
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        recorded_intent = {"url": "https://api.example.com"}
        recorded_result = {"status_code": 200, "body": {"data": "test"}}

        effect_records = [
            ModelEffectRecord(
                effect_type="http.get",
                intent=recorded_intent,
                result=recorded_result,
                captured_at=fixed_time,
                sequence_index=0,
            )
        ]

        replay_session = executor.create_replay_session(
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_records=effect_records,
        )

        # Get replay result
        result = replay_session.effect_recorder.get_replay_result(
            effect_type="http.get",
            intent=recorded_intent,
        )

        assert result == recorded_result


@pytest.mark.unit
class TestExecutorReplayFullCycle:
    """Test full record-then-replay determinism cycle."""

    def test_record_then_replay_determinism(self, executor: ExecutorReplay) -> None:
        """Test full cycle: record execution, then replay deterministically."""
        seed = 42

        # RECORD PHASE
        # Generate random values with known seed
        # Note: We must reset the RNG to get consistent sequences
        # Create a fresh recording session for the actual random capture
        recording_session2 = executor.create_recording_session(rng_seed=seed)
        recorded_randoms = [recording_session2.rng_service.random() for _ in range(3)]

        # Record an effect
        recording_session2.effect_recorder.record(
            effect_type="api.call",
            intent={"endpoint": "/users"},
            result={"users": ["alice", "bob"]},
        )

        # Capture updated manifest with effect records
        manifest = executor.capture_manifest(recording_session2)

        # REPLAY PHASE
        # Parse manifest data
        replay_time = datetime.fromisoformat(manifest["time_frozen_at"])
        replay_seed = manifest["rng_seed"]

        # Recreate effect records from manifest
        from omnibase_core.models.replay.model_effect_record import ModelEffectRecord

        effect_records = [
            ModelEffectRecord.model_validate(r) for r in manifest["effect_records"]
        ]

        # Create replay session
        replay_session = executor.create_replay_session(
            time_frozen_at=replay_time,
            rng_seed=replay_seed,
            effect_records=effect_records,
        )

        # Verify time determinism - replay time should equal manifest time
        replayed_time = replay_session.time_service.now()
        assert replayed_time == replay_time

        # Verify RNG determinism - same seed produces same sequence
        replayed_randoms = [replay_session.rng_service.random() for _ in range(3)]
        assert replayed_randoms == recorded_randoms

        # Verify effect determinism
        effect_result = replay_session.effect_recorder.get_replay_result(
            effect_type="api.call",
            intent={"endpoint": "/users"},
        )
        assert effect_result == {"users": ["alice", "bob"]}


@pytest.mark.unit
class TestExecutorReplaySessionModes:
    """Test session mode property."""

    def test_session_modes_correct(self, executor: ExecutorReplay) -> None:
        """Test session mode property returns correct value."""
        from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode

        prod_session = executor.create_production_session()
        assert prod_session.mode == EnumReplayMode.PRODUCTION

        rec_session = executor.create_recording_session()
        assert rec_session.mode == EnumReplayMode.RECORDING

        replay_session = executor.create_replay_session(
            time_frozen_at=datetime.now(UTC),
            rng_seed=42,
            effect_records=[],
        )
        assert replay_session.mode == EnumReplayMode.REPLAYING


@pytest.mark.unit
class TestExecutorReplaySessionOverwriteWarning:
    """Test warning when user provides replay_session in kwargs."""

    def test_execute_sync_warns_on_session_overwrite(
        self, executor: ExecutorReplay, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test sync execution warns when user provides replay_session in kwargs."""
        import logging

        session = executor.create_production_session()
        user_session = executor.create_production_session()  # User's session

        def get_session_id(replay_session: ReplaySession) -> UUID:
            return replay_session.session_id

        with caplog.at_level(logging.WARNING):
            result = executor.execute_sync(
                session, get_session_id, replay_session=user_session
            )

        # Should use executor's session, not user's
        assert result == session.session_id
        assert result != user_session.session_id

        # Should have warned
        assert "replay_session" in caplog.text
        assert "overwritten" in caplog.text

    @pytest.mark.asyncio
    async def test_execute_async_warns_on_session_overwrite(
        self, executor: ExecutorReplay, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test async execution warns when user provides replay_session in kwargs."""
        import logging

        session = executor.create_production_session()
        user_session = executor.create_production_session()  # User's session

        async def get_session_id(replay_session: ReplaySession) -> UUID:
            return replay_session.session_id

        with caplog.at_level(logging.WARNING):
            result = await executor.execute_async(
                session, get_session_id, replay_session=user_session
            )

        # Should use executor's session, not user's
        assert result == session.session_id
        assert result != user_session.session_id

        # Should have warned
        assert "replay_session" in caplog.text
        assert "overwritten" in caplog.text

    def test_execute_sync_no_warning_without_user_session(
        self, executor: ExecutorReplay, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test no warning when user doesn't provide replay_session."""
        import logging

        session = executor.create_production_session()

        def get_session_id(replay_session: ReplaySession) -> UUID:
            return replay_session.session_id

        with caplog.at_level(logging.WARNING):
            result = executor.execute_sync(session, get_session_id)

        # Should work normally
        assert result == session.session_id

        # Should NOT have warned
        assert "overwritten" not in caplog.text


@pytest.mark.unit
class TestReplaySession:
    """Test ReplaySession dataclass."""

    def test_session_has_unique_id(self, executor: ExecutorReplay) -> None:
        """Test each session has a unique session_id."""
        session1 = executor.create_production_session()
        session2 = executor.create_production_session()

        assert session1.session_id != session2.session_id
        assert isinstance(session1.session_id, UUID)

    def test_session_context_is_accessible(self, executor: ExecutorReplay) -> None:
        """Test session context is accessible."""
        session = executor.create_recording_session(rng_seed=42)

        assert session.context is not None
        assert session.context.rng_seed == 42
