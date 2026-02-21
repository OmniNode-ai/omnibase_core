# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelProjectionIntent.

Tests verify:
- Valid construction with required fields
- Field validation (min/max lengths, required fields)
- Immutability (frozen model)
- Extra fields rejected
- Serialization / round-trip
- __repr__ output
- from_attributes compatibility (pytest-xdist support)
- Envelope typed as BaseModel (polymorphic flexibility)
- Correlation ID validation (UUID format)

Test Organization:
    TestModelProjectionIntentConstruction  — creation and default values
    TestModelProjectionIntentValidation    — field constraint enforcement
    TestModelProjectionIntentImmutability  — frozen behavior
    TestModelProjectionIntentSerialization — model_dump / round-trip
    TestModelProjectionIntentRepr          — __repr__ output
    TestModelProjectionIntentFromAttributes — from_attributes support
    TestModelProjectionIntentEnvelope      — envelope field flexibility
    TestModelProjectionIntentEdgeCases     — boundary conditions
"""

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.projectors import ModelProjectionIntent

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a fresh correlation UUID for each test."""
    return uuid4()


class _SimpleEnvelope(BaseModel):
    """Minimal stand-in for a real event envelope."""

    envelope_id: str
    node_id: str


@pytest.fixture
def simple_envelope() -> _SimpleEnvelope:
    """Provide a minimal envelope model."""
    return _SimpleEnvelope(envelope_id="env-001", node_id="node-abc")


@pytest.fixture
def valid_intent(
    correlation_id: UUID, simple_envelope: _SimpleEnvelope
) -> ModelProjectionIntent:
    """Provide a fully populated ModelProjectionIntent."""
    return ModelProjectionIntent(
        projector_key="node_state_projector",
        event_type="node.created.v1",
        envelope=simple_envelope,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentConstruction:
    """Tests for ModelProjectionIntent construction."""

    def test_valid_construction_all_fields(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Construct with all required fields."""
        intent = ModelProjectionIntent(
            projector_key="node_state_projector",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert intent.projector_key == "node_state_projector"
        assert intent.event_type == "node.created.v1"
        assert intent.envelope is simple_envelope
        assert intent.correlation_id == correlation_id

    def test_all_fields_are_required(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """All four fields are required; omitting any raises ValidationError."""
        # Missing projector_key
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(  # type: ignore[call-arg]
                event_type="node.created.v1",
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "projector_key" in str(exc_info.value)

        # Missing event_type
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(  # type: ignore[call-arg]
                projector_key="node_state_projector",
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "event_type" in str(exc_info.value)

        # Missing envelope
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(  # type: ignore[call-arg]
                projector_key="node_state_projector",
                event_type="node.created.v1",
                correlation_id=correlation_id,
            )
        assert "envelope" in str(exc_info.value)

        # Missing correlation_id
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(  # type: ignore[call-arg]
                projector_key="node_state_projector",
                event_type="node.created.v1",
                envelope=simple_envelope,
            )
        assert "correlation_id" in str(exc_info.value)

    def test_correlation_id_as_string_accepted(
        self, simple_envelope: _SimpleEnvelope
    ) -> None:
        """String UUID is coerced to UUID object."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=uuid_str,  # type: ignore[arg-type]
        )
        assert str(intent.correlation_id) == uuid_str

    def test_correlation_id_invalid_format_rejected(
        self, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Non-UUID string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(
                projector_key="proj-1",
                event_type="node.created.v1",
                envelope=simple_envelope,
                correlation_id="not-a-uuid",  # type: ignore[arg-type]
            )
        assert "correlation_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentValidation:
    """Tests for field-level validation constraints."""

    def test_projector_key_min_length(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Empty projector_key is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(
                projector_key="",
                event_type="node.created.v1",
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "projector_key" in str(exc_info.value)

    def test_projector_key_max_length(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """projector_key exceeding 100 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(
                projector_key="x" * 101,
                event_type="node.created.v1",
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "projector_key" in str(exc_info.value)

    def test_projector_key_at_max_length_accepted(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """projector_key at exactly 100 chars is accepted."""
        intent = ModelProjectionIntent(
            projector_key="x" * 100,
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert len(intent.projector_key) == 100

    def test_event_type_min_length(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Empty event_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(
                projector_key="proj-1",
                event_type="",
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "event_type" in str(exc_info.value)

    def test_event_type_max_length(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """event_type exceeding 100 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(
                projector_key="proj-1",
                event_type="e" * 101,
                envelope=simple_envelope,
                correlation_id=correlation_id,
            )
        assert "event_type" in str(exc_info.value)

    def test_event_type_at_max_length_accepted(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """event_type at exactly 100 chars is accepted."""
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="e" * 100,
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert len(intent.event_type) == 100

    def test_extra_fields_rejected(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionIntent(  # type: ignore[call-arg]
                projector_key="proj-1",
                event_type="node.created.v1",
                envelope=simple_envelope,
                correlation_id=correlation_id,
                unknown_field="should fail",
            )
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_config_frozen(self) -> None:
        """ConfigDict has frozen=True."""
        assert ModelProjectionIntent.model_config.get("frozen") is True

    def test_config_extra_forbid(self) -> None:
        """ConfigDict has extra='forbid'."""
        assert ModelProjectionIntent.model_config.get("extra") == "forbid"

    def test_config_from_attributes(self) -> None:
        """ConfigDict has from_attributes=True."""
        assert ModelProjectionIntent.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentImmutability:
    """Tests for frozen (immutable) behavior."""

    def test_projector_key_immutable(self, valid_intent: ModelProjectionIntent) -> None:
        """Cannot reassign projector_key on frozen model."""
        with pytest.raises(ValidationError):
            valid_intent.projector_key = "changed"  # type: ignore[attr-defined]

    def test_event_type_immutable(self, valid_intent: ModelProjectionIntent) -> None:
        """Cannot reassign event_type on frozen model."""
        with pytest.raises(ValidationError):
            valid_intent.event_type = "changed.v2"  # type: ignore[attr-defined]

    def test_envelope_immutable(
        self, valid_intent: ModelProjectionIntent, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Cannot reassign envelope on frozen model."""
        with pytest.raises(ValidationError):
            valid_intent.envelope = simple_envelope  # type: ignore[attr-defined]

    def test_correlation_id_immutable(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """Cannot reassign correlation_id on frozen model."""
        with pytest.raises(ValidationError):
            valid_intent.correlation_id = uuid4()  # type: ignore[attr-defined]

    def test_hashable(self, correlation_id: UUID) -> None:
        """Frozen model with a frozen envelope is hashable (can be used in sets/dicts).

        Note: ModelProjectionIntent is frozen=True, but the envelope field is typed
        as BaseModel. Pydantic's hash implementation iterates over all field values,
        so the envelope itself must also be hashable (i.e., frozen). This tests that
        the contract holds when the caller provides a frozen envelope.
        """

        class FrozenEnvelope(BaseModel):
            model_config = {"frozen": True}
            envelope_id: str

        env = FrozenEnvelope(envelope_id="env-001")
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        h = hash(intent)
        assert isinstance(h, int)

    def test_hash_consistency(self, correlation_id: UUID) -> None:
        """Two identical intents (with frozen envelopes) produce the same hash."""

        class FrozenEnvelope(BaseModel):
            model_config = {"frozen": True}
            envelope_id: str

        env = FrozenEnvelope(envelope_id="env-001")
        intent1 = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        intent2 = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        assert hash(intent1) == hash(intent2)
        assert intent1 == intent2


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentSerialization:
    """Tests for serialization and round-trip behavior."""

    def test_model_dump_contains_required_fields(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """model_dump returns dict with all intent fields."""
        data = valid_intent.model_dump()
        assert "projector_key" in data
        assert "event_type" in data
        assert "envelope" in data
        assert "correlation_id" in data

    def test_model_dump_json_mode_uuid_serialized_as_string(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """In JSON mode, UUID is serialized as a string."""
        data = valid_intent.model_dump(mode="json")
        assert isinstance(data["correlation_id"], str)
        assert len(data["correlation_id"]) == 36

    def test_model_dump_json_mode_string_fields(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """String fields survive JSON mode serialization."""
        data = valid_intent.model_dump(mode="json")
        assert data["projector_key"] == "node_state_projector"
        assert data["event_type"] == "node.created.v1"

    def test_roundtrip_dict(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Intent survives a model_dump → model_validate round-trip."""
        original = ModelProjectionIntent(
            projector_key="proj-roundtrip",
            event_type="workflow.started.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        data = original.model_dump(mode="json", serialize_as_any=True)
        restored = ModelProjectionIntent.model_validate(data)

        assert restored.projector_key == original.projector_key
        assert restored.event_type == original.event_type
        assert str(restored.correlation_id) == str(original.correlation_id)

    def test_model_dump_json_string_valid(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """model_dump_json produces a valid JSON string."""
        import json

        json_str = valid_intent.model_dump_json(serialize_as_any=True)
        parsed = json.loads(json_str)
        assert parsed["projector_key"] == "node_state_projector"
        assert parsed["event_type"] == "node.created.v1"


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentRepr:
    """Tests for __repr__ output."""

    def test_repr_contains_class_name(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """repr contains 'ModelProjectionIntent'."""
        assert "ModelProjectionIntent" in repr(valid_intent)

    def test_repr_contains_projector_key(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """repr contains the projector_key value."""
        assert "node_state_projector" in repr(valid_intent)

    def test_repr_contains_event_type(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """repr contains the event_type value."""
        assert "node.created.v1" in repr(valid_intent)

    def test_repr_contains_correlation_id(
        self, valid_intent: ModelProjectionIntent
    ) -> None:
        """repr contains the correlation_id value."""
        assert str(valid_intent.correlation_id) in repr(valid_intent)

    def test_repr_is_string(self, valid_intent: ModelProjectionIntent) -> None:
        """repr returns a string."""
        assert isinstance(repr(valid_intent), str)


# ---------------------------------------------------------------------------
# from_attributes support
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentFromAttributes:
    """Tests for from_attributes=True (pytest-xdist compatibility)."""

    def test_from_attributes_enabled(self, correlation_id: UUID) -> None:
        """model_validate can construct from an attribute-bearing object."""

        class FakeEnvelope(BaseModel):
            node_id: str = "node-1"

        env = FakeEnvelope()

        class IntentLike:
            projector_key = "node_state_projector"
            event_type = "node.created.v1"
            envelope = env

            def __init__(self) -> None:
                self.correlation_id = correlation_id

        intent = ModelProjectionIntent.model_validate(IntentLike())
        assert intent.projector_key == "node_state_projector"
        assert intent.event_type == "node.created.v1"
        assert intent.correlation_id == correlation_id


# ---------------------------------------------------------------------------
# Envelope polymorphism
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentEnvelope:
    """Tests for envelope field flexibility."""

    def test_envelope_accepts_plain_base_model(self, correlation_id: UUID) -> None:
        """envelope accepts a plain BaseModel subclass."""

        class MinimalEnvelope(BaseModel):
            id: str

        env = MinimalEnvelope(id="e-1")
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        assert intent.envelope is env

    def test_envelope_accepts_complex_model(self, correlation_id: UUID) -> None:
        """envelope accepts a complex nested BaseModel."""

        class Payload(BaseModel):
            node_id: str
            tags: list[str]

        class ComplexEnvelope(BaseModel):
            envelope_id: str
            payload: Payload

        env = ComplexEnvelope(
            envelope_id="env-complex",
            payload=Payload(node_id="n-1", tags=["prod", "v2"]),
        )
        intent = ModelProjectionIntent(
            projector_key="complex_projector",
            event_type="workflow.completed.v2",
            envelope=env,
            correlation_id=correlation_id,
        )
        assert intent.envelope.envelope_id == "env-complex"  # type: ignore[attr-defined]
        assert intent.envelope.payload.node_id == "n-1"  # type: ignore[attr-defined]

    def test_multiple_intents_can_share_same_envelope(
        self, correlation_id: UUID
    ) -> None:
        """Multiple intents for different projectors can reference the same envelope."""

        class SharedEnvelope(BaseModel):
            envelope_id: str = "shared-env"

        env = SharedEnvelope()
        intent_a = ModelProjectionIntent(
            projector_key="projector_a",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        intent_b = ModelProjectionIntent(
            projector_key="projector_b",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        assert intent_a.envelope is intent_b.envelope
        assert intent_a.projector_key != intent_b.projector_key


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelProjectionIntentEdgeCases:
    """Tests for boundary conditions and edge cases."""

    def test_projector_key_single_char_accepted(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Single-character projector_key is at min_length and is accepted."""
        intent = ModelProjectionIntent(
            projector_key="p",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert intent.projector_key == "p"

    def test_event_type_single_char_accepted(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Single-character event_type is at min_length and is accepted."""
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="e",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert intent.event_type == "e"

    def test_different_projector_keys_produce_different_intents(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Intents with different projector_keys are not equal."""
        intent_a = ModelProjectionIntent(
            projector_key="projector_a",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        intent_b = ModelProjectionIntent(
            projector_key="projector_b",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert intent_a != intent_b

    def test_different_event_types_produce_different_intents(
        self, correlation_id: UUID, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Intents with different event_types are not equal."""
        intent_a = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        intent_b = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.deleted.v1",
            envelope=simple_envelope,
            correlation_id=correlation_id,
        )
        assert intent_a != intent_b

    def test_different_correlation_ids_produce_different_intents(
        self, simple_envelope: _SimpleEnvelope
    ) -> None:
        """Intents with different correlation_ids are not equal."""
        intent_a = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=uuid4(),
        )
        intent_b = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=simple_envelope,
            correlation_id=uuid4(),
        )
        assert intent_a != intent_b

    def test_intent_can_be_used_as_dict_key(self, correlation_id: UUID) -> None:
        """Frozen model with a frozen envelope can be used as a dict key."""

        class FrozenEnvelope(BaseModel):
            model_config = {"frozen": True}
            envelope_id: str

        env = FrozenEnvelope(envelope_id="env-001")
        intent = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        d = {intent: "processed"}
        assert d[intent] == "processed"

    def test_intent_can_be_added_to_set(self, correlation_id: UUID) -> None:
        """Two equal intents (with frozen envelopes) collapse to one element in a set."""

        class FrozenEnvelope(BaseModel):
            model_config = {"frozen": True}
            envelope_id: str

        env = FrozenEnvelope(envelope_id="env-001")
        intent1 = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        intent2 = ModelProjectionIntent(
            projector_key="proj-1",
            event_type="node.created.v1",
            envelope=env,
            correlation_id=correlation_id,
        )
        assert len({intent1, intent2}) == 1
