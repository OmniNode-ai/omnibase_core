"""Unit tests for ModelMessageEnvelope."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import Ed25519KeyPair, generate_keypair
from omnibase_core.crypto.crypto_file_key_provider import FileKeyProvider
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
def keypair() -> Ed25519KeyPair:
    """Generate a keypair for testing."""
    return generate_keypair()


@pytest.fixture
def key_provider(tmp_path: Path, keypair: Ed25519KeyPair) -> FileKeyProvider:
    """Create a key provider with a registered key."""
    provider = FileKeyProvider(tmp_path / "keys.json")
    provider.register_key("runtime-dev-001", keypair.public_key_bytes)
    return provider


@pytest.mark.unit
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
        with pytest.raises(ValidationError):
            # NOTE: Intentionally assigning to frozen field to verify immutability.
            # Mypy correctly flags this as an error since the model is frozen.
            identity.env = "prod"  # type: ignore[misc]

    def test_identity_requires_all_fields(self) -> None:
        """All fields are required."""
        with pytest.raises(ValidationError):
            # NOTE: Intentionally calling with missing required fields to test validation.
            # Mypy correctly flags this as missing required arguments.
            ModelEmitterIdentity(env="dev")  # type: ignore[call-arg]


@pytest.mark.unit
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
        with pytest.raises(ValidationError):
            # NOTE: Intentionally assigning to frozen field to verify immutability.
            # Mypy correctly flags this as an error since the model is frozen.
            signature.signer = "other"  # type: ignore[misc]

    def test_payload_hash_must_be_64_chars(self) -> None:
        """Payload hash must be exactly 64 characters."""
        with pytest.raises(ValidationError):
            ModelEnvelopeSignature(
                algorithm="ed25519",
                signer="runtime-dev-001",
                payload_hash="tooshort",
                signature="base64signature==",
            )

    def test_payload_hash_must_be_valid_hex(self) -> None:
        """Payload hash must contain only hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnvelopeSignature(
                algorithm="ed25519",
                signer="runtime-dev-001",
                payload_hash="g" * 64,  # 'g' is not a valid hex character
                signature="base64signature==",
            )
        assert "hex characters" in str(exc_info.value).lower()

    def test_payload_hash_normalized_to_lowercase(self) -> None:
        """Payload hash is normalized to lowercase."""
        signature = ModelEnvelopeSignature(
            algorithm="ed25519",
            signer="runtime-dev-001",
            payload_hash="ABCDEF" + "0" * 58,  # Uppercase hex
            signature="base64signature==",
        )
        assert signature.payload_hash == "abcdef" + "0" * 58  # Should be lowercase


@pytest.mark.unit
class TestModelMessageEnvelopeCreation:
    """Tests for creating ModelMessageEnvelope."""

    def test_create_signed_envelope(self, keypair: Ed25519KeyPair) -> None:
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

    def test_create_signed_with_emitter_identity(self, keypair: Ed25519KeyPair) -> None:
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

    def test_create_signed_with_optional_fields(self, keypair: Ed25519KeyPair) -> None:
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


@pytest.mark.unit
class TestModelMessageEnvelopeImmutability:
    """Tests for envelope immutability."""

    def test_envelope_is_frozen(self, keypair: Ed25519KeyPair) -> None:
        """Envelope model is immutable after creation."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )
        with pytest.raises(ValidationError):
            # NOTE: Intentionally assigning to frozen field to verify immutability.
            # Mypy correctly flags this as an error since the model is frozen.
            envelope.realm = "prod"  # type: ignore[misc]


@pytest.mark.unit
class TestModelMessageEnvelopeIdentityValidation:
    """Tests for identity/realm mismatch validation."""

    def test_identity_realm_mismatch_rejected(self, keypair: Ed25519KeyPair) -> None:
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

    def test_identity_realm_match_accepted(self, keypair: Ed25519KeyPair) -> None:
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


@pytest.mark.unit
class TestModelMessageEnvelopeSignerValidation:
    """Tests for signer/runtime_id mismatch validation."""

    def test_signer_mismatch_rejected(self, keypair: Ed25519KeyPair) -> None:
        """Envelope with mismatched signature.signer and runtime_id is rejected."""
        from datetime import UTC, datetime

        # Create a valid envelope first to get a valid signature
        valid_envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        # Try to construct an envelope with mismatched signer and runtime_id
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMessageEnvelope[dict](
                realm="dev",
                runtime_id="different-runtime",  # Different from signature.signer
                bus_id="kafka-cluster-a",
                trace_id=valid_envelope.trace_id,
                emitted_at=datetime.now(UTC),
                signature=valid_envelope.signature,  # signer is "runtime-dev-001"
                payload={"data": "test"},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.ENVELOPE_SIGNER_MISMATCH
        assert "runtime-dev-001" in str(exc_info.value)
        assert "different-runtime" in str(exc_info.value)

    def test_signer_match_accepted(self, keypair: Ed25519KeyPair) -> None:
        """Envelope with matching signature.signer and runtime_id is accepted."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        # Envelope should be created successfully with matching signer
        assert envelope.signature.signer == envelope.runtime_id


@pytest.mark.unit
class TestModelMessageEnvelopePayloadSerialization:
    """Tests for non-serializable payload handling."""

    def test_non_serializable_payload_in_create_signed_raises(
        self, keypair: Ed25519KeyPair
    ) -> None:
        """create_signed raises ModelOnexError for non-serializable payload."""

        class NonSerializable:
            def __init__(self):
                self.circular = self  # Circular reference

        with pytest.raises(ModelOnexError) as exc_info:
            ModelMessageEnvelope.create_signed(
                realm="dev",
                runtime_id="runtime-dev-001",
                bus_id="kafka-cluster-a",
                payload=NonSerializable(),
                private_key=keypair.private_key_bytes,
            )

        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.ENVELOPE_PAYLOAD_SERIALIZATION_FAILED
        )
        assert "NonSerializable" in str(exc_info.value)

    def test_non_serializable_payload_in_verify_signature_raises(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
        """verify_signature raises ModelOnexError for non-serializable payload."""
        from datetime import UTC, datetime
        from typing import Any

        # Create a valid envelope with a serializable payload
        valid_envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        # Create an object with a circular reference (cannot be JSON serialized)
        circular_obj: dict[str, Any] = {}
        circular_obj["self"] = circular_obj

        # Construct an envelope with a non-serializable dict payload
        # (bypassing create_signed which would catch this earlier)
        bad_envelope = ModelMessageEnvelope[dict](
            realm=valid_envelope.realm,
            runtime_id=valid_envelope.runtime_id,
            bus_id=valid_envelope.bus_id,
            trace_id=valid_envelope.trace_id,
            emitted_at=datetime.now(UTC),
            signature=valid_envelope.signature,
            payload=circular_obj,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            bad_envelope.verify_signature(key_provider)

        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.ENVELOPE_PAYLOAD_SERIALIZATION_FAILED
        )
        # Verify the error message mentions serialization failure
        assert "serialize payload" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelMessageEnvelopeSignatureVerification:
    """Tests for signature verification."""

    def test_verify_valid_signature(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
        """verify_signature returns True for valid signature."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
        )

        assert envelope.verify_signature(key_provider) is True

    def test_verify_unknown_runtime_raises(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
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

    def test_verify_wrong_key_returns_false(
        self, keypair: Ed25519KeyPair, tmp_path: Path
    ) -> None:
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

    def test_tampered_envelope_fails_verification(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
        """Tampering with envelope fields after signing causes verification to fail."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "original"},
            private_key=keypair.private_key_bytes,
        )

        # Verify original is valid
        assert envelope.verify_signature(key_provider) is True

        # Create tampered envelope by modifying a signed field
        # ModelMessageEnvelope is not frozen, so we can construct a modified copy
        tampered_envelope = ModelMessageEnvelope[dict](
            realm="prod",  # Changed from "dev" to "prod"
            runtime_id=envelope.runtime_id,
            bus_id=envelope.bus_id,
            trace_id=envelope.trace_id,
            emitted_at=envelope.emitted_at,
            signature=envelope.signature,  # Keep original signature
            payload=envelope.payload,
        )

        # Tampered envelope should fail verification
        assert tampered_envelope.verify_signature(key_provider) is False

    def test_tampered_payload_fails_verification(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
        """Tampering with payload after signing causes verification to fail."""
        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "original"},
            private_key=keypair.private_key_bytes,
        )

        # Verify original is valid
        assert envelope.verify_signature(key_provider) is True

        # Create envelope with tampered payload but same signature
        tampered_envelope = ModelMessageEnvelope[dict](
            realm=envelope.realm,
            runtime_id=envelope.runtime_id,
            bus_id=envelope.bus_id,
            trace_id=envelope.trace_id,
            emitted_at=envelope.emitted_at,
            signature=envelope.signature,  # Keep original signature
            payload={"data": "TAMPERED"},  # Different payload
        )

        # Tampered envelope should fail verification because payload_hash won't match
        assert tampered_envelope.verify_signature(key_provider) is False


@pytest.mark.unit
class TestModelMessageEnvelopeTimestampValidation:
    """Tests for timestamp validation."""

    def test_naive_datetime_rejected(self, keypair: Ed25519KeyPair) -> None:
        """Envelope with naive datetime (no timezone) is rejected."""
        naive_datetime = datetime(2025, 1, 1, 12, 0, 0)  # No tzinfo
        assert naive_datetime.tzinfo is None  # Confirm it's naive

        with pytest.raises(ValidationError) as exc_info:
            ModelMessageEnvelope.create_signed(
                realm="dev",
                runtime_id="runtime-dev-001",
                bus_id="kafka-cluster-a",
                payload={"data": "test"},
                private_key=keypair.private_key_bytes,
                emitted_at=naive_datetime,
            )

        assert "timezone-aware" in str(exc_info.value).lower()

    def test_timezone_aware_datetime_accepted(self, keypair: Ed25519KeyPair) -> None:
        """Envelope with timezone-aware datetime is accepted."""
        aware_datetime = datetime.now(UTC)
        assert aware_datetime.tzinfo is not None  # Confirm it's aware

        envelope = ModelMessageEnvelope.create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"data": "test"},
            private_key=keypair.private_key_bytes,
            emitted_at=aware_datetime,
        )

        assert envelope.emitted_at == aware_datetime


@pytest.mark.unit
class TestModelMessageEnvelopeWithDictPayload:
    """Tests for envelope with dict payloads."""

    def test_dict_payload(self, keypair: Ed25519KeyPair) -> None:
        """Envelope works with dict payload."""
        envelope = ModelMessageEnvelope[dict].create_signed(
            realm="dev",
            runtime_id="runtime-dev-001",
            bus_id="kafka-cluster-a",
            payload={"key": "value", "nested": {"a": 1}},
            private_key=keypair.private_key_bytes,
        )

        assert envelope.payload == {"key": "value", "nested": {"a": 1}}

    def test_dict_payload_signature_deterministic(
        self, keypair: Ed25519KeyPair
    ) -> None:
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


@pytest.mark.unit
class TestModelMessageEnvelopeFullFlow:
    """End-to-end tests for sign -> serialize -> verify flow."""

    def test_full_roundtrip(
        self, keypair: Ed25519KeyPair, key_provider: FileKeyProvider
    ) -> None:
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
