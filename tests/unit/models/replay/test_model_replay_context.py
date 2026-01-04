# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelReplayContext.

Tests all aspects of the replay context model including:
- Model instantiation and validation
- Frozen behavior (immutability)
- Default values and auto-generation
- Mode property helpers
- Immutable update methods
- Serialization/deserialization
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode
from omnibase_core.models.replay.model_replay_context import ModelReplayContext

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestModelReplayContextFrozen:
    """Test frozen behavior (immutability) of ModelReplayContext."""

    def test_model_is_frozen(self) -> None:
        """Test that model is frozen and fields cannot be reassigned."""
        ctx = ModelReplayContext()

        with pytest.raises(ValidationError):
            ctx.mode = EnumReplayMode.RECORDING

    def test_frozen_prevents_context_id_modification(self) -> None:
        """Test that frozen model prevents context_id modification."""
        ctx = ModelReplayContext()

        with pytest.raises(ValidationError):
            ctx.context_id = uuid4()

    def test_frozen_prevents_rng_seed_modification(self) -> None:
        """Test that frozen model prevents rng_seed modification."""
        ctx = ModelReplayContext(rng_seed=42)

        with pytest.raises(ValidationError):
            ctx.rng_seed = 100

    def test_frozen_prevents_new_attribute_assignment(self) -> None:
        """Test that frozen model prevents new attribute assignment."""
        ctx = ModelReplayContext()

        with pytest.raises(ValidationError):
            ctx.new_attr = "value"


@pytest.mark.unit
class TestModelReplayContextDefaults:
    """Test default values for ModelReplayContext."""

    def test_default_mode_is_production(self) -> None:
        """Test that default mode is PRODUCTION."""
        ctx = ModelReplayContext()

        assert ctx.mode == EnumReplayMode.PRODUCTION

    def test_context_id_auto_generated(self) -> None:
        """Test that context_id is auto-generated as UUID."""
        ctx = ModelReplayContext()

        assert ctx.context_id is not None
        assert isinstance(ctx.context_id, UUID)

    def test_created_at_auto_generated(self) -> None:
        """Test that created_at is auto-generated."""
        before = datetime.now(UTC)
        ctx = ModelReplayContext()
        after = datetime.now(UTC)

        assert ctx.created_at is not None
        assert isinstance(ctx.created_at, datetime)
        assert before <= ctx.created_at <= after

    def test_default_time_frozen_at_is_none(self) -> None:
        """Test that default time_frozen_at is None."""
        ctx = ModelReplayContext()

        assert ctx.time_frozen_at is None

    def test_default_rng_seed_is_none(self) -> None:
        """Test that default rng_seed is None."""
        ctx = ModelReplayContext()

        assert ctx.rng_seed is None

    def test_default_effect_record_ids_is_empty_tuple(self) -> None:
        """Test that default effect_record_ids is empty tuple."""
        ctx = ModelReplayContext()

        assert ctx.effect_record_ids == ()
        assert isinstance(ctx.effect_record_ids, tuple)

    def test_default_time_captures_is_empty_tuple(self) -> None:
        """Test that default time_captures is empty tuple."""
        ctx = ModelReplayContext()

        assert ctx.time_captures == ()
        assert isinstance(ctx.time_captures, tuple)

    def test_default_original_execution_id_is_none(self) -> None:
        """Test that default original_execution_id is None."""
        ctx = ModelReplayContext()

        assert ctx.original_execution_id is None


@pytest.mark.unit
class TestModelReplayContextModePropertyHelpers:
    """Test mode property helpers."""

    def test_is_production_property(self) -> None:
        """Test is_production property."""
        ctx = ModelReplayContext(mode=EnumReplayMode.PRODUCTION)

        assert ctx.is_production is True
        assert ctx.is_recording is False
        assert ctx.is_replaying is False

    def test_is_recording_property(self) -> None:
        """Test is_recording property."""
        ctx = ModelReplayContext(mode=EnumReplayMode.RECORDING)

        assert ctx.is_production is False
        assert ctx.is_recording is True
        assert ctx.is_replaying is False

    def test_is_replaying_property(self) -> None:
        """Test is_replaying property."""
        ctx = ModelReplayContext(mode=EnumReplayMode.REPLAYING)

        assert ctx.is_production is False
        assert ctx.is_recording is False
        assert ctx.is_replaying is True


@pytest.mark.unit
class TestModelReplayContextWithTimeCapture:
    """Test with_time_capture immutable update method."""

    def test_with_time_capture_returns_new_instance(self) -> None:
        """Test that with_time_capture returns a new instance."""
        ctx = ModelReplayContext()
        captured_time = datetime.now(UTC)

        new_ctx = ctx.with_time_capture(captured_time)

        assert new_ctx is not ctx
        assert isinstance(new_ctx, ModelReplayContext)

    def test_with_time_capture_adds_time(self) -> None:
        """Test that with_time_capture adds time to captures."""
        ctx = ModelReplayContext()
        captured_time = datetime.now(UTC)

        new_ctx = ctx.with_time_capture(captured_time)

        assert len(new_ctx.time_captures) == 1
        assert new_ctx.time_captures[0] == captured_time

    def test_with_time_capture_preserves_original(self) -> None:
        """Test that with_time_capture does not mutate original."""
        ctx = ModelReplayContext()
        captured_time = datetime.now(UTC)

        new_ctx = ctx.with_time_capture(captured_time)

        assert len(ctx.time_captures) == 0
        assert len(new_ctx.time_captures) == 1

    def test_with_time_capture_accumulates(self) -> None:
        """Test that with_time_capture accumulates multiple captures."""
        ctx = ModelReplayContext()
        time1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        time2 = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)
        time3 = datetime(2024, 1, 1, 12, 0, 2, tzinfo=UTC)

        ctx = ctx.with_time_capture(time1)
        ctx = ctx.with_time_capture(time2)
        ctx = ctx.with_time_capture(time3)

        assert len(ctx.time_captures) == 3
        assert ctx.time_captures == (time1, time2, time3)

    def test_with_time_capture_preserves_other_fields(self) -> None:
        """Test that with_time_capture preserves other fields."""
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=42,
        )
        captured_time = datetime.now(UTC)

        new_ctx = ctx.with_time_capture(captured_time)

        assert new_ctx.mode == EnumReplayMode.RECORDING
        assert new_ctx.rng_seed == 42
        assert new_ctx.context_id == ctx.context_id


@pytest.mark.unit
class TestModelReplayContextWithEffectRecord:
    """Test with_effect_record immutable update method."""

    def test_with_effect_record_returns_new_instance(self) -> None:
        """Test that with_effect_record returns a new instance."""
        ctx = ModelReplayContext()
        record_id = uuid4()

        new_ctx = ctx.with_effect_record(record_id)

        assert new_ctx is not ctx
        assert isinstance(new_ctx, ModelReplayContext)

    def test_with_effect_record_adds_id(self) -> None:
        """Test that with_effect_record adds record ID."""
        ctx = ModelReplayContext()
        record_id = uuid4()

        new_ctx = ctx.with_effect_record(record_id)

        assert len(new_ctx.effect_record_ids) == 1
        assert new_ctx.effect_record_ids[0] == record_id

    def test_with_effect_record_preserves_original(self) -> None:
        """Test that with_effect_record does not mutate original."""
        ctx = ModelReplayContext()
        record_id = uuid4()

        new_ctx = ctx.with_effect_record(record_id)

        assert len(ctx.effect_record_ids) == 0
        assert len(new_ctx.effect_record_ids) == 1

    def test_with_effect_record_accumulates(self) -> None:
        """Test that with_effect_record accumulates multiple records."""
        ctx = ModelReplayContext()
        id1 = uuid4()
        id2 = uuid4()
        id3 = uuid4()

        ctx = ctx.with_effect_record(id1)
        ctx = ctx.with_effect_record(id2)
        ctx = ctx.with_effect_record(id3)

        assert len(ctx.effect_record_ids) == 3
        assert ctx.effect_record_ids == (id1, id2, id3)

    def test_with_effect_record_preserves_other_fields(self) -> None:
        """Test that with_effect_record preserves other fields."""
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=42,
        )
        record_id = uuid4()

        new_ctx = ctx.with_effect_record(record_id)

        assert new_ctx.mode == EnumReplayMode.RECORDING
        assert new_ctx.rng_seed == 42
        assert new_ctx.context_id == ctx.context_id


@pytest.mark.unit
class TestModelReplayContextSerialization:
    """Test serialization and deserialization."""

    def test_serialization_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        original_exec_id = uuid4()

        ctx = ModelReplayContext(
            mode=EnumReplayMode.REPLAYING,
            time_frozen_at=fixed_time,
            rng_seed=42,
            original_execution_id=original_exec_id,
        )

        # Serialize to dict
        data = ctx.model_dump()

        # Deserialize
        restored = ModelReplayContext.model_validate(data)

        assert restored.mode == ctx.mode
        assert restored.time_frozen_at == ctx.time_frozen_at
        assert restored.rng_seed == ctx.rng_seed
        assert restored.original_execution_id == ctx.original_execution_id
        assert restored.context_id == ctx.context_id

    def test_json_serialization_roundtrip(self) -> None:
        """Test JSON string serialization roundtrip."""
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=123,
        )

        # Serialize to JSON string
        json_str = ctx.model_dump_json()

        # Deserialize from JSON string
        restored = ModelReplayContext.model_validate_json(json_str)

        assert restored.mode == ctx.mode
        assert restored.rng_seed == ctx.rng_seed

    def test_model_dump(self) -> None:
        """Test model_dump method."""
        ctx = ModelReplayContext(
            mode=EnumReplayMode.PRODUCTION,
            rng_seed=42,
        )

        data = ctx.model_dump()

        assert isinstance(data, dict)
        assert data["mode"] == "production"
        assert data["rng_seed"] == 42


@pytest.mark.unit
class TestModelReplayContextRecordingConfiguration:
    """Test recording mode configuration."""

    def test_recording_mode_configuration(self) -> None:
        """Test creating context for recording mode."""
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=42,
        )

        assert ctx.mode == EnumReplayMode.RECORDING
        assert ctx.is_recording is True
        assert ctx.rng_seed == 42

    def test_recording_mode_captures_time(self) -> None:
        """Test that recording mode can capture times."""
        ctx = ModelReplayContext(mode=EnumReplayMode.RECORDING)
        time1 = datetime.now(UTC)

        ctx = ctx.with_time_capture(time1)

        assert len(ctx.time_captures) == 1
        assert ctx.is_recording is True


@pytest.mark.unit
class TestModelReplayContextReplayingConfiguration:
    """Test replaying mode configuration."""

    def test_replaying_mode_configuration(self) -> None:
        """Test creating context for replay mode."""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        original_id = uuid4()
        effect_ids = (uuid4(), uuid4())

        ctx = ModelReplayContext(
            mode=EnumReplayMode.REPLAYING,
            time_frozen_at=fixed_time,
            rng_seed=42,
            effect_record_ids=effect_ids,
            original_execution_id=original_id,
        )

        assert ctx.mode == EnumReplayMode.REPLAYING
        assert ctx.is_replaying is True
        assert ctx.time_frozen_at == fixed_time
        assert ctx.rng_seed == 42
        assert ctx.effect_record_ids == effect_ids
        assert ctx.original_execution_id == original_id

    def test_replaying_requires_determinism_data(self) -> None:
        """Test that replay mode should typically have determinism data."""
        # This is a semantic test - replay mode without time/seed is unusual
        ctx = ModelReplayContext(mode=EnumReplayMode.REPLAYING)

        # Model allows this, but it's semantically unusual
        assert ctx.is_replaying is True
        assert ctx.time_frozen_at is None
        assert ctx.rng_seed is None


@pytest.mark.unit
class TestModelReplayContextExtraFieldsRejected:
    """Test that extra fields are rejected (extra='forbid')."""

    def test_extra_fields_rejected_at_construction(self) -> None:
        """Test that extra fields are rejected during construction."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplayContext(
                extra_field="should_be_rejected",
            )

        error_str = str(exc_info.value)
        assert "extra_field" in error_str.lower() or "extra" in error_str.lower()

    def test_extra_fields_rejected_via_model_validate(self) -> None:
        """Test that extra fields are rejected via model_validate."""
        data = {
            "mode": "production",
            "extra_field": "should_be_rejected",
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelReplayContext.model_validate(data)

        error_str = str(exc_info.value)
        assert "extra_field" in error_str.lower() or "extra" in error_str.lower()


@pytest.mark.unit
class TestModelReplayContextEquality:
    """Test model equality."""

    def test_model_equality(self) -> None:
        """Test that models with same values are equal."""
        fixed_id = uuid4()
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        ctx1 = ModelReplayContext(
            context_id=fixed_id,
            mode=EnumReplayMode.PRODUCTION,
            rng_seed=42,
            created_at=fixed_time,
        )
        ctx2 = ModelReplayContext(
            context_id=fixed_id,
            mode=EnumReplayMode.PRODUCTION,
            rng_seed=42,
            created_at=fixed_time,
        )

        assert ctx1 == ctx2

    def test_model_inequality_different_mode(self) -> None:
        """Test that models with different modes are not equal."""
        fixed_id = uuid4()
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        ctx1 = ModelReplayContext(
            context_id=fixed_id,
            mode=EnumReplayMode.PRODUCTION,
            created_at=fixed_time,
        )
        ctx2 = ModelReplayContext(
            context_id=fixed_id,
            mode=EnumReplayMode.RECORDING,
            created_at=fixed_time,
        )

        assert ctx1 != ctx2


@pytest.mark.unit
class TestModelReplayContextTimeCaptures:
    """Test time captures tuple behavior."""

    def test_time_captures_is_tuple(self) -> None:
        """Test that time_captures is a tuple."""
        times = (
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC),
        )
        ctx = ModelReplayContext(time_captures=times)

        assert isinstance(ctx.time_captures, tuple)
        assert ctx.time_captures == times

    def test_time_captures_from_list(self) -> None:
        """Test that list is converted to tuple."""
        times = [
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC),
        ]
        ctx = ModelReplayContext(time_captures=times)

        assert isinstance(ctx.time_captures, tuple)
        assert len(ctx.time_captures) == 2


@pytest.mark.unit
class TestModelReplayContextEffectRecordIds:
    """Test effect record IDs tuple behavior."""

    def test_effect_record_ids_is_tuple(self) -> None:
        """Test that effect_record_ids is a tuple."""
        ids = (uuid4(), uuid4(), uuid4())
        ctx = ModelReplayContext(effect_record_ids=ids)

        assert isinstance(ctx.effect_record_ids, tuple)
        assert ctx.effect_record_ids == ids

    def test_effect_record_ids_from_list(self) -> None:
        """Test that list is converted to tuple."""
        ids = [uuid4(), uuid4()]
        ctx = ModelReplayContext(effect_record_ids=ids)

        assert isinstance(ctx.effect_record_ids, tuple)
        assert len(ctx.effect_record_ids) == 2
