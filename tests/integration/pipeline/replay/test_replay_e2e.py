# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
End-to-end integration tests for replay infrastructure.

These tests verify the core replay invariant:
    Same inputs + Same context -> Same outputs

Test categories:
1. Time determinism - Fixed time produces identical results
2. RNG determinism - Same seed produces identical sequences
3. Effect stubbing - Recorded effects replay correctly
4. Full pipeline replay - Complete execution replay

Related:
    - OMN-1116: Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7.1

.. versionadded:: 0.4.0
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.enums.replay import EnumRecorderMode, EnumReplayMode
from omnibase_core.models.replay import ModelEffectRecord, ModelReplayContext
from omnibase_core.pipeline.replay import (
    ServiceEffectRecorder,
    ServiceRNGInjector,
    ServiceTimeInjector,
)


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestTimeDeterminism:
    """Tests for time injection determinism.

    Verifies that fixed time produces identical results across executions.
    """

    def test_time_sensitive_function_with_fixed_time(self) -> None:
        """Function using time produces same result with fixed time.

        Verifies:
        - ServiceTimeInjector with fixed_time returns that time consistently
        - Multiple executions with same fixed time produce identical results
        """
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        def time_sensitive_func(time_svc: ServiceTimeInjector) -> str:
            return f"Generated at {time_svc.now().isoformat()}"

        # Execute twice with same fixed time
        result1 = time_sensitive_func(ServiceTimeInjector(fixed_time=fixed_time))
        result2 = time_sensitive_func(ServiceTimeInjector(fixed_time=fixed_time))

        assert result1 == result2
        assert "2024-06-15T12:00:00" in result1

    def test_time_frozen_across_multiple_calls(self) -> None:
        """Multiple time.now() calls return the same fixed time.

        Verifies:
        - ServiceTimeInjector with fixed_time is frozen
        - All calls to now() return identical values
        """
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        time_svc = ServiceTimeInjector(fixed_time=fixed_time)

        times = [time_svc.now() for _ in range(100)]

        assert all(t == fixed_time for t in times)

    def test_time_capture_in_replay_context(self) -> None:
        """Time values can be captured in ModelReplayContext.

        Verifies:
        - ModelReplayContext tracks time captures
        - with_time_capture returns new immutable context
        - Multiple captures are stored in order
        """
        ctx = ModelReplayContext(mode=EnumReplayMode.RECORDING, rng_seed=42)
        time1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        time2 = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)

        # Capture times immutably
        ctx = ctx.with_time_capture(time1)
        ctx = ctx.with_time_capture(time2)

        assert len(ctx.time_captures) == 2
        assert ctx.time_captures[0] == time1
        assert ctx.time_captures[1] == time2

    def test_naive_datetime_assumes_utc(self) -> None:
        """Naive datetime is treated as UTC.

        Verifies:
        - ServiceTimeInjector accepts naive datetimes
        - Naive datetimes are interpreted as UTC
        """
        naive_time = datetime(2024, 6, 15, 12, 0, 0)  # No tzinfo
        time_svc = ServiceTimeInjector(fixed_time=naive_time)

        result = time_svc.now()

        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_utc_now_alias(self) -> None:
        """utc_now() is an alias for now().

        Verifies:
        - Both methods return identical results
        - API consistency is maintained
        """
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        time_svc = ServiceTimeInjector(fixed_time=fixed_time)

        assert time_svc.now() == time_svc.utc_now()


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestRNGDeterminism:
    """Tests for RNG injection determinism.

    Verifies that same seed produces identical random sequences.
    """

    def test_random_function_with_seed(self) -> None:
        """Function using RNG produces same result with same seed.

        Verifies:
        - ServiceRNGInjector with same seed produces identical sequences
        - random() method is deterministic
        """

        def random_func(rng: ServiceRNGInjector) -> list[float]:
            return [rng.random() for _ in range(5)]

        result1 = random_func(ServiceRNGInjector(seed=42))
        result2 = random_func(ServiceRNGInjector(seed=42))

        assert result1 == result2

    def test_random_choices_with_seed(self) -> None:
        """Random choices are deterministic with same seed.

        Verifies:
        - choice() method produces identical sequences with same seed
        - Selection from sequences is reproducible
        """
        options = ["a", "b", "c", "d", "e"]

        def choose_func(rng: ServiceRNGInjector) -> list[str]:
            return [rng.choice(options) for _ in range(10)]

        result1 = choose_func(ServiceRNGInjector(seed=123))
        result2 = choose_func(ServiceRNGInjector(seed=123))

        assert result1 == result2

    def test_randint_with_seed(self) -> None:
        """randint() is deterministic with same seed.

        Verifies:
        - randint() produces identical sequences with same seed
        - Range bounds are respected
        """

        def dice_rolls(rng: ServiceRNGInjector) -> list[int]:
            return [rng.randint(1, 6) for _ in range(20)]

        result1 = dice_rolls(ServiceRNGInjector(seed=999))
        result2 = dice_rolls(ServiceRNGInjector(seed=999))

        assert result1 == result2
        assert all(1 <= x <= 6 for x in result1)

    def test_mixed_rng_operations_deterministic(self) -> None:
        """Mixed RNG operations are deterministic.

        Verifies:
        - Combining random(), randint(), and choice() is deterministic
        - Operation order matters and is preserved
        """

        def mixed_ops(rng: ServiceRNGInjector) -> dict[str, Any]:
            return {
                "float1": rng.random(),
                "int1": rng.randint(1, 100),
                "choice1": rng.choice(["red", "green", "blue"]),
                "float2": rng.random(),
                "int2": rng.randint(1, 1000),
                "choice2": rng.choice(list("abcdefghij")),
            }

        result1 = mixed_ops(ServiceRNGInjector(seed=42))
        result2 = mixed_ops(ServiceRNGInjector(seed=42))

        assert result1 == result2

    def test_seed_property_returns_seed(self) -> None:
        """seed property returns the seed used.

        Verifies:
        - Explicit seed is accessible via property
        - Auto-generated seed is also accessible
        """
        explicit_rng = ServiceRNGInjector(seed=12345)
        assert explicit_rng.seed == 12345

        auto_rng = ServiceRNGInjector()
        assert isinstance(auto_rng.seed, int)

    def test_different_seeds_produce_different_sequences(self) -> None:
        """Different seeds produce different sequences.

        Verifies:
        - Seed actually affects output (not hardcoded)
        - Statistical independence of different seeds
        """

        def random_func(rng: ServiceRNGInjector) -> list[float]:
            return [rng.random() for _ in range(5)]

        result1 = random_func(ServiceRNGInjector(seed=42))
        result2 = random_func(ServiceRNGInjector(seed=99))

        assert result1 != result2, "Different seeds should produce different results"


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestEffectRecording:
    """Tests for effect recording and replay.

    Verifies that recorded effects return same results on replay.
    """

    def test_recorded_effect_replays_correctly(self) -> None:
        """Recorded effects return same results on replay.

        Verifies:
        - ServiceEffectRecorder captures effects in RECORDING mode
        - Replay returns exact same result for matching effect_id and intent
        """
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Recording phase
        recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
            time_service=ServiceTimeInjector(fixed_time=fixed_time),
        )
        _record = recorder.record(
            effect_type="api.call",
            intent={"endpoint": "/users", "method": "GET"},
            result={"users": [{"id": 1, "name": "Alice"}]},
        )

        # Replay phase
        replay_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorder.get_all_records(),
        )
        replay_result = replay_recorder.get_replay_result(
            effect_type="api.call",
            intent={"endpoint": "/users", "method": "GET"},
        )

        assert replay_result == {"users": [{"id": 1, "name": "Alice"}]}

    def test_multiple_effects_replay_correctly(self) -> None:
        """Multiple recorded effects replay in correct order.

        Verifies:
        - Multiple effects can be recorded
        - Each effect replays with correct result based on intent
        """
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Recording phase
        recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
            time_service=ServiceTimeInjector(fixed_time=fixed_time),
        )

        # Record multiple effects
        recorder.record(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users"},
            result={"status": 200, "body": [{"id": 1}]},
        )
        recorder.record(
            effect_type="http.post",
            intent={"url": "https://api.example.com/users", "body": {"name": "Bob"}},
            result={"status": 201, "body": {"id": 2}},
        )
        recorder.record(
            effect_type="db.query",
            intent={"sql": "SELECT * FROM users"},
            result={"rows": [{"id": 1}, {"id": 2}]},
        )

        # Replay phase
        replay_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorder.get_all_records(),
        )

        # Verify each replay
        assert replay_recorder.get_replay_result(
            effect_type="http.get",
            intent={"url": "https://api.example.com/users"},
        ) == {"status": 200, "body": [{"id": 1}]}

        assert replay_recorder.get_replay_result(
            effect_type="http.post",
            intent={"url": "https://api.example.com/users", "body": {"name": "Bob"}},
        ) == {"status": 201, "body": {"id": 2}}

        assert replay_recorder.get_replay_result(
            effect_type="db.query",
            intent={"sql": "SELECT * FROM users"},
        ) == {"rows": [{"id": 1}, {"id": 2}]}

    def test_sequence_index_increments(self) -> None:
        """Sequence index increments for each recorded effect.

        Verifies:
        - Each record gets unique sequence_index
        - Index starts at 0 and increments
        """
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)

        r0 = recorder.record("e1", {"k": "v1"}, {"r": 1})
        r1 = recorder.record("e2", {"k": "v2"}, {"r": 2})
        r2 = recorder.record("e3", {"k": "v3"}, {"r": 3})

        assert r0.sequence_index == 0
        assert r1.sequence_index == 1
        assert r2.sequence_index == 2

    def test_effect_record_is_immutable(self) -> None:
        """ModelEffectRecord is immutable (frozen).

        Verifies:
        - Record cannot be modified after creation
        - Pydantic frozen=True is effective
        """
        record = ModelEffectRecord(
            effect_type="test",
            intent={"key": "value"},
            result={"data": "result"},
            captured_at=datetime.now(UTC),
            sequence_index=0,
        )

        with pytest.raises(Exception):  # ValidationError for frozen model
            record.effect_type = "modified"

    def test_pass_through_mode_no_recording(self) -> None:
        """Pass-through mode does not store records.

        Verifies:
        - PASS_THROUGH mode creates records but does not store them
        - get_all_records() returns empty list
        """
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.PASS_THROUGH)
        recorder.record("effect1", {"k": "v"}, {"r": 1})
        recorder.record("effect2", {"k": "v"}, {"r": 2})

        assert len(recorder.get_all_records()) == 0

    def test_replay_returns_none_for_unrecorded_effect(self) -> None:
        """Replay returns None for effects not in recording.

        Verifies:
        - Missing effects return None, not error
        - Partial intent mismatch returns None
        """
        recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
        )
        recorder.record(
            effect_type="known.effect",
            intent={"key": "specific_value"},
            result={"data": "result"},
        )

        replay_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorder.get_all_records(),
        )

        # Unknown effect_id
        assert (
            replay_recorder.get_replay_result(
                effect_type="unknown.effect",
                intent={"key": "specific_value"},
            )
            is None
        )

        # Wrong intent
        assert (
            replay_recorder.get_replay_result(
                effect_type="known.effect",
                intent={"key": "different_value"},
            )
            is None
        )

    def test_error_effect_recording(self) -> None:
        """Failed effects are recorded with error information.

        Verifies:
        - success=False flag is recorded
        - error_message is preserved
        """
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)

        error_record = recorder.record(
            effect_type="db.query",
            intent={"sql": "SELECT * FROM nonexistent"},
            result={},
            success=False,
            error_message="Table 'nonexistent' does not exist",
        )

        assert error_record.success is False
        assert error_record.error_message == "Table 'nonexistent' does not exist"


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestFullPipelineReplay:
    """Tests for complete pipeline replay scenarios.

    Verifies full execute -> capture -> replay cycle.
    """

    def test_execute_capture_replay_cycle(self) -> None:
        """Full cycle: execute -> capture -> replay -> verify identical.

        Verifies the core replay invariant:
            Same inputs + Same context -> Same outputs

        This is the most critical test proving deterministic replay.
        """

        def complex_operation(
            time_svc: ServiceTimeInjector,
            rng_svc: ServiceRNGInjector,
            effect_recorder: ServiceEffectRecorder,
        ) -> dict[str, Any]:
            """Operation using time, RNG, and effects."""
            timestamp = time_svc.now().isoformat()
            random_value = rng_svc.random()
            random_id = rng_svc.randint(1, 100)

            # Simulate effect (in recording mode, this captures; in replay, returns stub)
            if effect_recorder.is_recording:
                effect_result: dict[str, Any] = {
                    "external_data": f"fetched_{random_id}"
                }
                effect_recorder.record(
                    effect_type="fetch.data",
                    intent={"key": "test"},
                    result=effect_result,
                )
            elif effect_recorder.is_replaying:
                replay_result = effect_recorder.get_replay_result(
                    effect_type="fetch.data",
                    intent={"key": "test"},
                )
                effect_result = replay_result if replay_result else {}
            else:
                effect_result = {"external_data": "live_data"}

            return {
                "timestamp": timestamp,
                "random": random_value,
                "random_id": random_id,
                "effect": effect_result,
            }

        # RECORDING PHASE
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        recording_time = ServiceTimeInjector(fixed_time=fixed_time)
        recording_rng = ServiceRNGInjector(seed=42)
        recording_effects = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
            time_service=recording_time,
        )

        result1 = complex_operation(recording_time, recording_rng, recording_effects)

        # Capture manifest
        manifest: dict[str, Any] = {
            "time_frozen_at": fixed_time,
            "rng_seed": 42,
            "effect_records": recording_effects.get_all_records(),
        }

        # REPLAY PHASE
        replay_time = ServiceTimeInjector(fixed_time=manifest["time_frozen_at"])
        replay_rng = ServiceRNGInjector(seed=manifest["rng_seed"])
        replay_effects = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=manifest["effect_records"],
        )

        result2 = complex_operation(replay_time, replay_rng, replay_effects)

        # VERIFY DETERMINISM
        assert result1 == result2, (
            f"Replay produced different result: {result1} != {result2}"
        )

    def test_complex_workflow_determinism(self) -> None:
        """Complex multi-step workflow produces identical results on replay.

        Verifies:
        - Multiple sequential operations are deterministic
        - State accumulation is reproducible
        - All non-determinism sources are controlled

        Note:
            When RNG values are used inside effects, those values become part of
            the effect result and are NOT consumed from the RNG stream during
            replay. To ensure determinism for operations that depend on RNG after
            effects, those operations must ALSO be recorded as effects.

            This demonstrates the correct pattern: any code path that uses RNG
            should either:
            1. Use RNG BEFORE all effects (so RNG state is identical), OR
            2. Record the RNG-dependent operation as an effect itself.
        """

        def multi_step_workflow(
            time_svc: ServiceTimeInjector,
            rng_svc: ServiceRNGInjector,
            effect_recorder: ServiceEffectRecorder,
        ) -> dict[str, Any]:
            """Multi-step workflow with dependencies between steps."""
            results: dict[str, Any] = {"steps": [], "final_timestamp": None}

            # Step 1: Generate random IDs (BEFORE any effects, RNG state is identical)
            step1_ids = [rng_svc.randint(1000, 9999) for _ in range(3)]
            results["steps"].append({"name": "generate_ids", "ids": step1_ids})

            # Step 2: Fetch data for each ID (simulated with effects)
            # The RNG values used here are recorded as part of the effect result.
            step2_data: list[dict[str, Any]] = []
            for id_ in step1_ids:
                if effect_recorder.is_recording:
                    fetch_result = {"id": id_, "value": rng_svc.random()}
                    effect_recorder.record(
                        effect_type="fetch.by_id",
                        intent={"id": id_},
                        result=fetch_result,
                    )
                    step2_data.append(fetch_result)
                elif effect_recorder.is_replaying:
                    replay_result = effect_recorder.get_replay_result(
                        effect_type="fetch.by_id",
                        intent={"id": id_},
                    )
                    if replay_result:
                        step2_data.append(replay_result)
                else:
                    step2_data.append({"id": id_, "value": rng_svc.random()})
            results["steps"].append({"name": "fetch_data", "data": step2_data})

            # Step 3: Process with timestamp
            step3_timestamp = time_svc.now().isoformat()
            results["steps"].append({"name": "process", "timestamp": step3_timestamp})

            # Step 4: Final selection - ALSO recorded as an effect because
            # the RNG state has diverged after Step 2 (recording consumed RNG,
            # replay did not).
            if step2_data:
                if effect_recorder.is_recording:
                    final_choice = rng_svc.choice(step2_data)
                    effect_recorder.record(
                        effect_type="select.random",
                        intent={"count": len(step2_data)},
                        result={"selected": final_choice},
                    )
                elif effect_recorder.is_replaying:
                    select_result = effect_recorder.get_replay_result(
                        effect_type="select.random",
                        intent={"count": len(step2_data)},
                    )
                    final_choice = select_result["selected"] if select_result else {}
                else:
                    final_choice = rng_svc.choice(step2_data)
                results["steps"].append({"name": "select", "choice": final_choice})

            results["final_timestamp"] = time_svc.now().isoformat()

            return results

        # RECORDING
        fixed_time = datetime(2024, 12, 1, 10, 30, 0, tzinfo=UTC)
        rec_time = ServiceTimeInjector(fixed_time=fixed_time)
        rec_rng = ServiceRNGInjector(seed=7777)
        rec_effects = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
            time_service=rec_time,
        )

        original_result = multi_step_workflow(rec_time, rec_rng, rec_effects)
        recorded_effects = rec_effects.get_all_records()

        # REPLAY
        replay_time = ServiceTimeInjector(fixed_time=fixed_time)
        replay_rng = ServiceRNGInjector(seed=7777)
        replay_effects = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorded_effects,
        )

        replayed_result = multi_step_workflow(replay_time, replay_rng, replay_effects)

        # VERIFY
        assert original_result == replayed_result

    def test_replay_context_model_integration(self) -> None:
        """ModelReplayContext integrates with injectors.

        Verifies:
        - ModelReplayContext can store all determinism data
        - Context can be used to reconstruct replay state
        """
        # Create initial context
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=42,
        )

        # Simulate execution and capture
        time_svc = ServiceTimeInjector()
        captured_time = time_svc.now()
        ctx = ctx.with_time_capture(captured_time)

        # Record effect
        record = ModelEffectRecord(
            effect_type="test.effect",
            intent={"key": "value"},
            result={"data": "result"},
            captured_at=captured_time,
            sequence_index=0,
        )
        ctx = ctx.with_effect_record(record.record_id)

        # Verify context state
        assert ctx.is_recording
        assert ctx.rng_seed == 42
        assert len(ctx.time_captures) == 1
        assert len(ctx.effect_record_ids) == 1

        # Create replay context from recorded data
        replay_ctx = ModelReplayContext(
            mode=EnumReplayMode.REPLAYING,
            time_frozen_at=ctx.time_captures[0],
            rng_seed=ctx.rng_seed,
            effect_record_ids=ctx.effect_record_ids,
            original_execution_id=ctx.context_id,
        )

        assert replay_ctx.is_replaying
        assert replay_ctx.time_frozen_at == captured_time
        assert replay_ctx.rng_seed == 42
        assert replay_ctx.original_execution_id == ctx.context_id


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestManifestSerialization:
    """Tests for manifest serialization and roundtrip.

    Verifies that replay state can be persisted and restored.
    """

    def test_effect_record_json_roundtrip(self) -> None:
        """ModelEffectRecord survives JSON serialization roundtrip.

        Verifies:
        - Record can be serialized to JSON
        - Deserialized record matches original
        """
        original = ModelEffectRecord(
            effect_type="http.get",
            intent={"url": "https://api.example.com", "headers": {"auth": "token"}},
            result={"status": 200, "body": {"data": [1, 2, 3]}},
            captured_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
            sequence_index=5,
            success=True,
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = ModelEffectRecord.model_validate_json(json_str)

        assert restored.effect_type == original.effect_type
        assert restored.intent == original.intent
        assert restored.result == original.result
        assert restored.sequence_index == original.sequence_index
        assert restored.success == original.success

    def test_replay_context_json_roundtrip(self) -> None:
        """ModelReplayContext survives JSON serialization roundtrip.

        Verifies:
        - Context can be serialized to JSON
        - Deserialized context matches original
        """
        record_id = uuid4()
        original = ModelReplayContext(
            mode=EnumReplayMode.REPLAYING,
            time_frozen_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
            time_captures=(
                datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
                datetime(2024, 6, 15, 12, 0, 1, tzinfo=UTC),
            ),
            rng_seed=42,
            effect_record_ids=(record_id,),
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = ModelReplayContext.model_validate_json(json_str)

        assert restored.mode == original.mode
        assert restored.time_frozen_at == original.time_frozen_at
        assert restored.rng_seed == original.rng_seed
        assert len(restored.time_captures) == 2
        assert len(restored.effect_record_ids) == 1

    def test_full_manifest_roundtrip(self) -> None:
        """Full replay manifest survives JSON roundtrip.

        Verifies:
        - Complete manifest with context and records can be serialized
        - Replay using restored manifest produces identical results
        """

        def deterministic_func(
            time_svc: ServiceTimeInjector,
            rng_svc: ServiceRNGInjector,
        ) -> dict[str, Any]:
            return {
                "time": time_svc.now().isoformat(),
                "values": [rng_svc.random() for _ in range(3)],
                "choice": rng_svc.choice(["a", "b", "c"]),
            }

        # Execute and capture
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        time_svc = ServiceTimeInjector(fixed_time=fixed_time)
        rng_svc = ServiceRNGInjector(seed=42)

        original_result = deterministic_func(time_svc, rng_svc)

        # Create manifest
        manifest = {
            "time_frozen_at": fixed_time.isoformat(),
            "rng_seed": 42,
        }

        # Serialize and restore
        manifest_json = json.dumps(manifest)
        restored_manifest = json.loads(manifest_json)

        # Replay with restored manifest
        replay_time = ServiceTimeInjector(
            fixed_time=datetime.fromisoformat(restored_manifest["time_frozen_at"])
        )
        replay_rng = ServiceRNGInjector(seed=restored_manifest["rng_seed"])

        replayed_result = deterministic_func(replay_time, replay_rng)

        assert original_result == replayed_result


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestEdgeCases:
    """Edge case and error handling tests.

    Verifies graceful handling of unusual situations.
    """

    def test_replay_with_wrong_seed_produces_different_results(self) -> None:
        """Verify that wrong seed actually produces different results.

        This is a sanity check that the RNG seed is actually being used.
        """

        def random_func(rng: ServiceRNGInjector) -> list[float]:
            return [rng.random() for _ in range(5)]

        result1 = random_func(ServiceRNGInjector(seed=42))
        result2 = random_func(ServiceRNGInjector(seed=99))

        assert result1 != result2, "Different seeds should produce different results"

    def test_production_mode_uses_real_time(self) -> None:
        """Production mode uses actual current time.

        Verifies:
        - ServiceTimeInjector without fixed_time uses real time
        - Time is within expected bounds
        """
        time_svc = ServiceTimeInjector()  # No fixed time
        before = datetime.now(UTC)
        result = time_svc.now()
        after = datetime.now(UTC)

        assert before <= result <= after
        assert result.tzinfo == UTC

    def test_empty_effect_records_replay(self) -> None:
        """Replay with empty records returns None for all queries.

        Verifies:
        - Empty records list is handled gracefully
        - get_replay_result returns None, not error
        """
        replay_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=[],
        )

        result = replay_recorder.get_replay_result(
            effect_type="any.effect",
            intent={"any": "intent"},
        )

        assert result is None

    def test_recorder_mode_properties(self) -> None:
        """Recorder mode properties are accurate.

        Verifies:
        - is_recording property
        - is_replaying property
        - Mode flags are mutually exclusive (for non-pass-through)
        """
        recording = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        replaying = ServiceEffectRecorder(mode=EnumRecorderMode.REPLAYING, records=[])
        pass_through = ServiceEffectRecorder(mode=EnumRecorderMode.PASS_THROUGH)

        assert recording.is_recording is True
        assert recording.is_replaying is False

        assert replaying.is_recording is False
        assert replaying.is_replaying is True

        assert pass_through.is_recording is False
        assert pass_through.is_replaying is False

    def test_get_all_records_returns_copy(self) -> None:
        """get_all_records returns a copy, not internal list.

        Verifies:
        - Modifying returned list doesn't affect internal state
        - Data encapsulation is maintained
        """
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        recorder.record("e1", {"k": "v"}, {"r": 1})

        records = recorder.get_all_records()
        original_length = len(records)

        # Try to modify the returned list
        records.clear()

        # Internal state should be unchanged
        assert len(recorder.get_all_records()) == original_length

    def test_nested_intent_matching(self) -> None:
        """Replay matches nested intent structures exactly.

        Verifies:
        - Complex nested dicts are matched exactly
        - Order-independent matching (dict equality)
        """
        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        complex_intent = {
            "level1": {
                "level2": {
                    "values": [1, 2, 3],
                    "flag": True,
                }
            },
            "metadata": {"version": "1.0"},
        }

        recorder.record(
            effect_type="nested.effect",
            intent=complex_intent,
            result={"matched": True},
        )

        replay = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorder.get_all_records(),
        )

        # Same structure should match
        result = replay.get_replay_result("nested.effect", complex_intent)
        assert result == {"matched": True}

        # Different structure should not match
        different_intent = {
            "level1": {"level2": {"values": [1, 2], "flag": True}},  # Missing value
            "metadata": {"version": "1.0"},
        }
        result2 = replay.get_replay_result("nested.effect", different_intent)
        assert result2 is None


@pytest.mark.integration
@pytest.mark.replay
@pytest.mark.timeout(60)
class TestReplayInvariants:
    """Tests that verify the core replay invariants from the spec.

    These tests prove the fundamental guarantees of the replay system.
    """

    def test_invariant_same_inputs_same_outputs(self) -> None:
        """
        Invariant from MIXINS_TO_HANDLERS_REFACTOR.md:

        manifest_1 = await pipeline.execute(node, envelope, time=T, rng=R, effects=STUBS)
        manifest_2 = await pipeline.execute(node, envelope, time=T, rng=R, effects=STUBS)
        assert manifest_1.hook_trace == manifest_2.hook_trace

        Simplified version without actual pipeline execution.
        """

        def deterministic_operation(
            time_svc: ServiceTimeInjector, rng_svc: ServiceRNGInjector
        ) -> dict[str, Any]:
            return {
                "time": time_svc.now().isoformat(),
                "values": [rng_svc.random() for _ in range(3)],
            }

        T = datetime(2024, 1, 1, tzinfo=UTC)
        R = 12345

        manifest_1 = deterministic_operation(
            ServiceTimeInjector(fixed_time=T),
            ServiceRNGInjector(seed=R),
        )
        manifest_2 = deterministic_operation(
            ServiceTimeInjector(fixed_time=T),
            ServiceRNGInjector(seed=R),
        )

        assert manifest_1 == manifest_2

    def test_invariant_recording_then_replay_identical(self) -> None:
        """
        Invariant: Recording and replaying produces identical output.

        execute(recording_mode) == execute(replay_mode with recorded data)
        """

        def operation(
            time_svc: ServiceTimeInjector,
            rng_svc: ServiceRNGInjector,
            effect_recorder: ServiceEffectRecorder,
        ) -> dict[str, Any]:
            values = [rng_svc.random() for _ in range(5)]
            timestamp = time_svc.now().isoformat()

            if effect_recorder.is_recording:
                external_data = {"computed": sum(values)}
                effect_recorder.record(
                    effect_type="compute.sum",
                    intent={"values": values},
                    result=external_data,
                )
            elif effect_recorder.is_replaying:
                replay_result = effect_recorder.get_replay_result(
                    effect_type="compute.sum",
                    intent={"values": values},
                )
                external_data = replay_result if replay_result else {}
            else:
                external_data = {"computed": sum(values)}

            return {
                "timestamp": timestamp,
                "values": values,
                "external": external_data,
            }

        # Recording phase
        fixed_time = datetime(2024, 3, 15, 9, 0, 0, tzinfo=UTC)
        seed = 999

        rec_result = operation(
            ServiceTimeInjector(fixed_time=fixed_time),
            ServiceRNGInjector(seed=seed),
            ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING),
        )

        # We need to re-run recording to get the records
        rec_recorder = ServiceEffectRecorder(
            mode=EnumRecorderMode.RECORDING,
            time_service=ServiceTimeInjector(fixed_time=fixed_time),
        )
        rec_result = operation(
            ServiceTimeInjector(fixed_time=fixed_time),
            ServiceRNGInjector(seed=seed),
            rec_recorder,
        )

        # Replay phase
        replay_result = operation(
            ServiceTimeInjector(fixed_time=fixed_time),
            ServiceRNGInjector(seed=seed),
            ServiceEffectRecorder(
                mode=EnumRecorderMode.REPLAYING,
                records=rec_recorder.get_all_records(),
            ),
        )

        assert rec_result == replay_result

    def test_invariant_determinism_across_multiple_replays(self) -> None:
        """
        Invariant: Multiple replays produce identical results.

        replay_1 == replay_2 == replay_3 == ... == replay_N
        """

        def operation(
            time_svc: ServiceTimeInjector, rng_svc: ServiceRNGInjector
        ) -> dict[str, Any]:
            return {
                "timestamp": time_svc.now().isoformat(),
                "random_values": [rng_svc.random() for _ in range(10)],
                "random_ints": [rng_svc.randint(1, 100) for _ in range(10)],
                "random_choices": [
                    rng_svc.choice(["a", "b", "c", "d", "e"]) for _ in range(10)
                ],
            }

        fixed_time = datetime(2024, 7, 4, 12, 0, 0, tzinfo=UTC)
        seed = 42

        # Execute multiple replays
        replays = [
            operation(
                ServiceTimeInjector(fixed_time=fixed_time),
                ServiceRNGInjector(seed=seed),
            )
            for _ in range(10)
        ]

        # All replays should be identical
        first_replay = replays[0]
        for i, replay in enumerate(replays[1:], start=2):
            assert replay == first_replay, f"Replay {i} differs from replay 1"

    def test_invariant_time_is_frozen_during_replay(self) -> None:
        """
        Invariant: Time does not advance during replay.

        All time queries return the same frozen time.
        """
        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        time_svc = ServiceTimeInjector(fixed_time=fixed_time)

        # Simulate multiple time queries during a long operation
        times = []
        for _ in range(1000):
            times.append(time_svc.now())

        # All times should be identical
        assert all(t == fixed_time for t in times)
        assert len(set(times)) == 1  # Only one unique time

    def test_invariant_rng_sequence_is_deterministic(self) -> None:
        """
        Invariant: RNG produces same sequence every time with same seed.

        sequence_1 == sequence_2 when seed_1 == seed_2
        """
        seed = 12345

        def generate_sequence(rng: ServiceRNGInjector) -> list[Any]:
            return [
                rng.random(),
                rng.randint(1, 100),
                rng.choice(["x", "y", "z"]),
                rng.random(),
                rng.randint(1000, 9999),
                rng.choice(list(range(100))),
            ]

        seq1 = generate_sequence(ServiceRNGInjector(seed=seed))
        seq2 = generate_sequence(ServiceRNGInjector(seed=seed))
        seq3 = generate_sequence(ServiceRNGInjector(seed=seed))

        assert seq1 == seq2 == seq3

    def test_invariant_effects_return_recorded_values(self) -> None:
        """
        Invariant: Effects return exactly what was recorded.

        replay_result == recorded_result
        """
        recorded_result = {
            "complex_data": {
                "nested": {"values": [1, 2, 3]},
                "metadata": {"version": "1.0", "timestamp": "2024-06-15T12:00:00"},
            },
            "status": "success",
            "items": [{"id": 1}, {"id": 2}, {"id": 3}],
        }

        recorder = ServiceEffectRecorder(mode=EnumRecorderMode.RECORDING)
        recorder.record(
            effect_type="complex.effect",
            intent={"action": "fetch"},
            result=recorded_result,
        )

        replay = ServiceEffectRecorder(
            mode=EnumRecorderMode.REPLAYING,
            records=recorder.get_all_records(),
        )

        replay_result = replay.get_replay_result(
            effect_type="complex.effect",
            intent={"action": "fetch"},
        )

        assert replay_result == recorded_result
