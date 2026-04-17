# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPersistStateIntent."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.intents import ModelCoreIntent, ModelPersistStateIntent
from omnibase_core.models.state import ModelStateEnvelope

# ---- Fixtures ----


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a fresh correlation ID for each test."""
    return uuid4()


@pytest.fixture
def intent_id() -> UUID:
    """Provide a fresh intent ID for each test."""
    return uuid4()


@pytest.fixture
def emitted_at() -> datetime:
    """Provide a timezone-aware emitted_at timestamp."""
    return datetime.now(UTC)


@pytest.fixture
def sample_envelope() -> ModelStateEnvelope:
    """Provide a sample ModelStateEnvelope."""
    return ModelStateEnvelope(
        node_id="node-abc",
        scope_id="default",
        data={"status": "active", "count": 3},
        written_at=datetime.now(UTC),
        contract_fingerprint="abc123",
    )


@pytest.fixture
def sample_intent(
    intent_id: UUID,
    sample_envelope: ModelStateEnvelope,
    emitted_at: datetime,
    correlation_id: UUID,
) -> ModelPersistStateIntent:
    """Provide a fully-constructed ModelPersistStateIntent."""
    return ModelPersistStateIntent(
        intent_id=intent_id,
        envelope=sample_envelope,
        emitted_at=emitted_at,
        correlation_id=correlation_id,
    )


# ---- Tests ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelPersistStateIntent:
    """Tests for ModelPersistStateIntent."""

    def test_valid_construction(
        self,
        intent_id: UUID,
        sample_envelope: ModelStateEnvelope,
        emitted_at: datetime,
        correlation_id: UUID,
    ) -> None:
        """Test valid intent construction with all required fields."""
        intent = ModelPersistStateIntent(
            intent_id=intent_id,
            envelope=sample_envelope,
            emitted_at=emitted_at,
            correlation_id=correlation_id,
        )
        assert intent.intent_id == intent_id
        assert intent.envelope == sample_envelope
        assert intent.emitted_at == emitted_at
        assert intent.correlation_id == correlation_id

    def test_inherits_from_core_intent(self) -> None:
        """ModelPersistStateIntent must inherit from ModelCoreIntent."""
        assert issubclass(ModelPersistStateIntent, ModelCoreIntent)

    def test_config_frozen(self) -> None:
        """Test that the model is frozen (immutable)."""
        assert ModelPersistStateIntent.model_config.get("frozen") is True

    def test_config_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        assert ModelPersistStateIntent.model_config.get("extra") == "forbid"

    def test_config_from_attributes(self) -> None:
        """Test from_attributes is enabled for pytest-xdist compatibility."""
        assert ModelPersistStateIntent.model_config.get("from_attributes") is True

    def test_immutability(self, sample_intent: ModelPersistStateIntent) -> None:
        """Test that mutation raises ValidationError (frozen model)."""
        with pytest.raises(ValidationError):
            sample_intent.intent_id = uuid4()  # type: ignore[misc]

    def test_missing_intent_id_raises(
        self,
        sample_envelope: ModelStateEnvelope,
        emitted_at: datetime,
        correlation_id: UUID,
    ) -> None:
        """intent_id is required — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPersistStateIntent(
                envelope=sample_envelope,
                emitted_at=emitted_at,
                correlation_id=correlation_id,
            )
        assert "intent_id" in str(exc_info.value)

    def test_missing_envelope_raises(
        self,
        intent_id: UUID,
        emitted_at: datetime,
        correlation_id: UUID,
    ) -> None:
        """envelope is required — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPersistStateIntent(
                intent_id=intent_id,
                emitted_at=emitted_at,
                correlation_id=correlation_id,
            )
        assert "envelope" in str(exc_info.value)

    def test_missing_emitted_at_raises(
        self,
        intent_id: UUID,
        sample_envelope: ModelStateEnvelope,
        correlation_id: UUID,
    ) -> None:
        """emitted_at is required — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPersistStateIntent(
                intent_id=intent_id,
                envelope=sample_envelope,
                correlation_id=correlation_id,
            )
        assert "emitted_at" in str(exc_info.value)

    def test_missing_correlation_id_raises(
        self,
        intent_id: UUID,
        sample_envelope: ModelStateEnvelope,
        emitted_at: datetime,
    ) -> None:
        """correlation_id is required (from base) — omitting raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPersistStateIntent(
                intent_id=intent_id,
                envelope=sample_envelope,
                emitted_at=emitted_at,
            )
        assert "correlation_id" in str(exc_info.value)

    def test_extra_field_raises(
        self,
        intent_id: UUID,
        sample_envelope: ModelStateEnvelope,
        emitted_at: datetime,
        correlation_id: UUID,
    ) -> None:
        """Unexpected extra fields must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelPersistStateIntent(
                intent_id=intent_id,
                envelope=sample_envelope,
                emitted_at=emitted_at,
                correlation_id=correlation_id,
                unexpected_field="nope",
            )

    def test_serialize_for_io(self, sample_intent: ModelPersistStateIntent) -> None:
        """serialize_for_io must produce JSON-serializable dict."""
        data = sample_intent.serialize_for_io()
        assert isinstance(data, dict)
        assert str(sample_intent.intent_id) == data["intent_id"]
        assert str(sample_intent.correlation_id) == data["correlation_id"]
        assert data["envelope"]["node_id"] == "node-abc"
        assert data["envelope"]["data"] == {"status": "active", "count": 3}

    def test_envelope_fields_accessible(
        self, sample_intent: ModelPersistStateIntent
    ) -> None:
        """The wrapped envelope's fields are accessible through the intent."""
        assert sample_intent.envelope.node_id == "node-abc"
        assert sample_intent.envelope.scope_id == "default"
        assert sample_intent.envelope.data["status"] == "active"

    def test_emitted_at_is_timezone_aware(
        self,
        intent_id: UUID,
        sample_envelope: ModelStateEnvelope,
        correlation_id: UUID,
    ) -> None:
        """emitted_at should carry timezone info — naive datetimes are an error source."""
        aware_dt = datetime.now(UTC)
        intent = ModelPersistStateIntent(
            intent_id=intent_id,
            envelope=sample_envelope,
            emitted_at=aware_dt,
            correlation_id=correlation_id,
        )
        assert intent.emitted_at.tzinfo is not None
