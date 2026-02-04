"""Unit tests for ModelMessageEnvelope."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.crypto.ed25519_signer import generate_keypair
from omnibase_core.crypto.file_key_provider import FileKeyProvider
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.envelope.model_envelope_signature import (
    ModelEnvelopeSignature,
)
from omnibase_core.models.envelope.model_message_envelope import (
    ModelEmitterIdentity,
    ModelMessageEnvelope,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class SamplePayload(BaseModel):
    """Sample payload for testing."""

    message: str
    count: int


@pytest.fixture
def keypair():
    """Generate a keypair for testing."""
    return generate_keypair()


@pytest.fixture
def key_provider(tmp_path, keypair):
    """Create a key provider with a registered key."""
    provider = FileKeyProvider(tmp_path / "keys.json")
    provider.register_key("runtime-dev-001", keypair.public_key_bytes)
    return provider


class TestModelEmitterIdentity:
    """Tests for ModelEmitterIdentity model."""

    def test_create_valid_identity(self) -> None:
        """Can create valid emitter identity."""
        identity = ModelEmitterIdentity(
            env="dev",
            service="my-service",
            node_name="my-handler",
            version="v1",
        )
        assert identity.env == "dev"
        assert identity.service == "my-service"
        assert identity.node_name == "my-handler"
        assert identity.version == "v1"

    def test_identity_is_frozen(self) -> None:
        """Identity model is immutable."""
        identity = ModelEmitterIdentity(
            env="dev",
            service="my-service",
            node_name="my-handler",
            version="v1",
        )
        with pytest.raises(Exception):  # ValidationError for frozen model
            identity.env = "prod"  # type: ignore[misc]

    def test_identity_requires_all_fields(self) -> None:
        """All fields are required."""
        with pytest.raises(Exception):
            ModelEmitterIdentity(env="dev")  # type: ignore[call-arg]


class TestModelEnvelopeSignature:
    """Tests for ModelEnvelopeSignature model."""

    def test_create_valid_signature(self) -> None:
        """Can create valid signature model."""
        signature = ModelEnvelopeSignature(
            algorithm="ed25519",
            signer="runtime-dev-001",
            payload_hash="a" * 64,
            signature="base64signature==",
        )
        assert signature.algorithm == "ed25519"
        assert signature.signer == "runtime-dev-001"

    def test_signature_is_frozen(self) -> None:
        """Signature model is immutable."""
        signature = ModelEnvelopeSignature(
            algorithm="ed25519",
            signer="runtime-dev-001",
            payload_hash="a" * 64,
            signature="base64signature==",
        )
        with pytest.raises(Exception):
            signature.signer = "other"  # type: ignore[misc]

    def test_payload_hash_must_be_64_chars(self) -> None:
        """Payload hash must be exactly 64 characters."""
        with pytest.raises(Exception):
            ModelEnvelopeSignature(
                algorithm="ed25519",
                signer="runtime-dev-001",
                payload_hash="tooshort",
                signature="base64signature==",
            )


class TestModelMessageEnvelopeCreation:
    """Tests for creating ModelMessageEnvelope."""

    def test_create_signed_envelope(self, keypair) -> None:
        """create_signed creates valid signed envelope."""
        payload = SamplePayload(message="hello", count=42)

        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload=payload,
            private_key=keypair.private_key_bytes,
        )

        assert envelope.realm == "dev"
        assert envelope.runtime_id == "runtime-dev-001"
        assert envelope.bus_id == "kafka-cluster-a"
        assert envelope.payload == payload
        assert envelope.signature.signer == "runtime-dev-001"
        assert envelope.signature.algorithm == "ed25519"

    def test_create_signed_with_emitter_identity(self, keypair) -> None:
        """create_signed works with emitter_identity."""

        class MockIdentity:
            env = "dev"
            service = "my-service"
            node_name = "my-handler"
            version = "v1"

        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
            emitter_identity=MockIdentity(),
        )

        assert envelope.emitter_identity is not None
        assert envelope.emitter_identity.env == "dev"
        assert envelope.emitter_identity.service == "my-service"

    def test_create_signed_with_optional_fields(self, keypair) -> None:
        """create_signed accepts optional fields."""
        trace_id = uuid4()
        causality_id = uuid4()
        timestamp = datetime.now(UTC)

        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
            trace_id=trace_id,
            causality_id=causality_id,
            tenant_id="tenant-001",
            emitted_at=timestamp,
        )

        assert envelope.trace_id == trace_id
        assert envelope.causality_id == causality_id
        assert envelope.tenant_id == "tenant-001"
        assert envelope.emitted_at == timestamp


class TestModelMessageEnvelopeIdentityValidation:
    """Tests for identity/realm mismatch validation."""

    def test_identity_realm_mismatch_rejected(self, keypair) -> None:
        """Envelope with mismatched identity.env and realm is rejected."""

        class MismatchedIdentity:
            env = "prod"  # Different from realm
            service = "my-service"
            node_name = "my-handler"
            version = "v1"

        with pytest.raises(ModelOnexError) as exc_info:
            ModelMessageEnvelope.create_signed(
                realm="dev",  # realm is "dev"
                runtime_id="runtime-dev-001",
                bus_id="kafka-cluster-a",
                payload={"data": "test"},
                private_key=keypair.private_key_bytes,
                emitter_identity=MismatchedIdentity(),  # but identity.env is "prod"
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.ENVELOPE_IDENTITY_MISMATCH
        assert "emitter_identity.env='prod'" in str(exc_info.value)
        assert "realm='dev'" in str(exc_info.value)

    def test_identity_realm_match_accepted(self, keypair) -> None:
        """Envelope with matching identity.env and realm is accepted."""

        class MatchingIdentity:
            env = "dev"
            service = "my-service"
            node_name = "my-handler"
            version = "v1"

        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
            emitter_identity=MatchingIdentity(),
        )

        assert envelope.emitter_identity is not None
        assert envelope.emitter_identity.env == envelope.realm


class TestModelMessageEnvelopeSignatureVerification:
    """Tests for signature verification."""

    def test_verify_valid_signature(self, keypair, key_provider) -> None:
        """verify_signature returns True for valid signature."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        assert envelope.verify_signature(key_provider) is True

    def test_verify_unknown_runtime_raises(self, keypair, key_provider) -> None:
        """verify_signature raises for unknown runtime_id."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="unknown-runtime",  # Not registered
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            envelope.verify_signature(key_provider)

        assert exc_info.value.error_code == EnumCoreErrorCode.ENVELOPE_KEY_NOT_FOUND
        assert "unknown-runtime" in str(exc_info.value)

    def test_verify_wrong_key_returns_false(self, keypair, tmp_path) -> None:
        """verify_signature returns False for wrong key."""
        # Create envelope with one keypair
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        # Register a different key
        wrong_keypair = generate_keypair()
        provider = FileKeyProvider(tmp_path / "keys.json")
        provider.register_key("runtime-dev-001", wrong_keypair.public_key_bytes)

        assert envelope.verify_signature(provider) is False


class TestModelMessageEnvelopeWithDictPayload:
    """Tests for envelope with dict payloads."""

    def test_dict_payload(self, keypair) -> None:
        """Envelope works with dict payload."""
        envelope = ModelMessageEnvelope[dict].create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"key": "value", "nested": {"a": 1}},
            private_key=keypair.private_key_bytes,
        )

        assert envelope.payload == {"key": "value", "nested": {"a": 1}}

    def test_dict_payload_signature_deterministic(self, keypair) -> None:
        """Dict payloads produce deterministic signatures regardless of key order."""
        # Create two envelopes with same data but different key order
        payload1 = {"b": 2, "a": 1}
        payload2 = {"a": 1, "b": 2}
        timestamp = datetime.now(UTC)
        trace_id = uuid4()

        envelope1 = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload=payload1,
            private_key=keypair.private_key_bytes,
            emitted_at=timestamp,
            trace_id=trace_id,
        )

        envelope2 = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload=payload2,
            private_key=keypair.private_key_bytes,
            emitted_at=timestamp,
            trace_id=trace_id,
        )

        # Payload hashes should be identical due to canonical JSON
        assert envelope1.signature.payload_hash == envelope2.signature.payload_hash


class TestModelMessageEnvelopeFullFlow:
    """End-to-end tests for sign → serialize → verify flow."""

    def test_full_roundtrip(self, keypair, key_provider) -> None:
        """Complete sign → serialize → deserialize → verify flow."""
        # Create and sign
        original = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"message": "hello world"},
            private_key=keypair.private_key_bytes,
            tenant_id="tenant-001",
        )

        # Serialize to JSON
        json_data = original.model_dump_json()

        # Deserialize
        restored = ModelMessageEnvelope[dict].model_validate_json(json_data)

        # Verify signature
        assert restored.verify_signature(key_provider) is True

        # Verify all fields match
        assert restored.realm == original.realm
        assert restored.runtime_id == original.runtime_id
        assert restored.bus_id == original.bus_id
        assert restored.payload == original.payload
        assert restored.tenant_id == original.tenant_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
