"""
Tests for ModelSecureEventEnvelope encryption and decryption methods.

This module tests the AES-256-GCM encryption/decryption functionality
for secure event envelope payloads, including round-trip verification,
error handling, and metadata validation.
"""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.core.model_route_spec import ModelRouteSpec
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.security.model_encryption_metadata import (
    ModelEncryptionMetadata,
)
from omnibase_core.models.security.model_secure_event_envelope_class import (
    ModelSecureEventEnvelope,
)


@pytest.fixture
def sample_node_id():
    """Provide a consistent node ID for tests."""
    return uuid4()


@pytest.fixture
def sample_payload(sample_node_id) -> ModelOnexEvent:
    """Create a valid ModelOnexEvent for testing."""
    return ModelOnexEvent(
        event_type="core.node.start",
        node_id=sample_node_id,
        timestamp=datetime.now(UTC),
        event_id=uuid4(),
    )


@pytest.fixture
def sample_complex_payload(sample_node_id) -> ModelOnexEvent:
    """Create a complex ModelOnexEvent with metadata for testing."""
    return ModelOnexEvent(
        event_type="user.mycompany.workflow_complete",
        node_id=sample_node_id,
        timestamp=datetime.now(UTC),
        event_id=uuid4(),
        correlation_id=uuid4(),
    )


@pytest.fixture
def sample_envelope(sample_payload, sample_node_id) -> ModelSecureEventEnvelope:
    """Create a valid ModelSecureEventEnvelope for testing."""
    route_spec = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")
    return ModelSecureEventEnvelope(
        payload=sample_payload,
        route_spec=route_spec,
        source_node_id=sample_node_id,
        content_hash="a" * 64,  # Initial content hash
    )


@pytest.fixture
def complex_envelope(
    sample_complex_payload, sample_node_id
) -> ModelSecureEventEnvelope:
    """Create a complex ModelSecureEventEnvelope for testing."""
    route_spec = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")
    return ModelSecureEventEnvelope(
        payload=sample_complex_payload,
        route_spec=route_spec,
        source_node_id=sample_node_id,
        content_hash="b" * 64,
    )


@pytest.fixture
def encryption_key() -> str:
    """Provide a test encryption key."""
    return "test-encryption-key-for-aes-256-gcm"


@pytest.fixture
def different_encryption_key() -> str:
    """Provide a different encryption key for negative testing."""
    return "different-encryption-key-for-testing"


@pytest.mark.unit
class TestEncryptPayloadSuccess:
    """Test successful encryption scenarios."""

    def test_encrypt_payload_with_valid_key_sets_encrypted_state_and_metadata(
        self, sample_envelope, encryption_key
    ):
        """Test that encrypting a payload with a valid key sets encrypted state and metadata."""
        # Verify initial state
        assert sample_envelope.is_encrypted is False
        assert sample_envelope.encrypted_payload is None
        assert sample_envelope.encryption_metadata is None

        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)

        # Assert encryption completed successfully
        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encrypted_payload is not None

        # Verify encrypted_payload is valid base64
        try:
            decoded = base64.b64decode(sample_envelope.encrypted_payload)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"encrypted_payload is not valid base64: {e}")

        # Verify encryption_metadata is set with correct algorithm
        assert sample_envelope.encryption_metadata is not None
        assert sample_envelope.encryption_metadata.algorithm == "AES-256-GCM"

    def test_encrypt_payload_with_complex_payload_succeeds_and_sets_metadata(
        self, complex_envelope, encryption_key
    ):
        """Test that encryption with a complex payload containing multiple fields succeeds.

        Verifies that payloads with correlation_id and other optional fields
        are encrypted successfully with proper metadata.
        """
        complex_envelope.encrypt_payload(encryption_key)

        assert complex_envelope.is_encrypted is True
        assert complex_envelope.encrypted_payload is not None
        assert complex_envelope.encryption_metadata is not None
        assert complex_envelope.encryption_metadata.algorithm == "AES-256-GCM"


@pytest.mark.unit
class TestEncryptPayloadErrors:
    """Test encryption error scenarios."""

    def test_encrypt_already_encrypted_raises_error(
        self, sample_envelope, encryption_key
    ):
        """Test that encrypting an already encrypted envelope raises an error."""
        # First encryption
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Second encryption should raise ModelOnexError with INVALID_OPERATION
        # (encrypting already-encrypted payload is an invalid operation on the current state)
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.encrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_OPERATION
        assert "already encrypted" in str(exc_info.value.message).lower()

    def test_encrypt_with_unsupported_algorithm_raises_error(
        self, sample_envelope, encryption_key
    ):
        """Test that using an unsupported algorithm raises an error."""
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.encrypt_payload(encryption_key, algorithm="AES-128-CBC")

        # UNSUPPORTED_OPERATION is the correct code for unsupported algorithms
        assert exc_info.value.error_code == EnumCoreErrorCode.UNSUPPORTED_OPERATION
        assert "unsupported" in str(exc_info.value.message).lower()


@pytest.mark.unit
class TestDecryptPayloadSuccess:
    """Test successful decryption scenarios."""

    def test_decrypt_payload_with_correct_key_returns_original_data(
        self, sample_envelope, encryption_key
    ):
        """Test that decrypting a payload with the correct key returns the original data."""
        # Store original payload for comparison
        original_event_type = sample_envelope.payload.event_type
        original_node_id = sample_envelope.payload.node_id

        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Decrypt the payload
        decrypted_payload = sample_envelope.decrypt_payload(encryption_key)

        # Verify the decrypted payload matches the original
        assert decrypted_payload.event_type == original_event_type
        assert decrypted_payload.node_id == original_node_id


@pytest.mark.unit
class TestDecryptPayloadErrors:
    """Test decryption error scenarios."""

    def test_decrypt_not_encrypted_raises_error(self, sample_envelope, encryption_key):
        """Test that decrypting an unencrypted envelope raises an error."""
        # Envelope is not encrypted
        assert sample_envelope.is_encrypted is False

        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        # INVALID_OPERATION is the correct code for decrypting a non-encrypted envelope
        # (decryption is not valid for the current state)
        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_OPERATION
        assert "not encrypted" in str(exc_info.value.message).lower()

    def test_decrypt_missing_metadata_raises_error(
        self, sample_envelope, encryption_key
    ):
        """Test that decrypting with missing metadata raises an error."""
        # Manually set is_encrypted without proper metadata
        sample_envelope.is_encrypted = True
        sample_envelope.encrypted_payload = None
        sample_envelope.encryption_metadata = None

        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "missing" in str(exc_info.value.message).lower()

    def test_decrypt_missing_encrypted_payload_raises_error(
        self, sample_envelope, encryption_key
    ):
        """Test that decrypting with missing encrypted_payload raises an error."""
        # Set encrypted flag but only provide metadata, no actual encrypted payload
        sample_envelope.is_encrypted = True
        sample_envelope.encrypted_payload = None
        sample_envelope.encryption_metadata = ModelEncryptionMetadata(
            algorithm="AES-256-GCM",
            key_id=uuid4(),
            iv=base64.b64encode(b"0123456789ab").decode("utf-8"),
            auth_tag=base64.b64encode(b"0123456789abcdef").decode("utf-8"),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
class TestRoundTripEncryption:
    """Test round-trip encryption and decryption scenarios."""

    def test_round_trip_encrypt_decrypt_preserves_all_payload_fields(
        self, complex_envelope, encryption_key
    ):
        """Test that encrypt->decrypt preserves data integrity for all payload fields.

        Verifies that event_type, node_id, and correlation_id are all preserved
        after a full encryption/decryption round trip.
        """
        # Store original payload for comparison
        original_event_type = complex_envelope.payload.event_type
        original_node_id = complex_envelope.payload.node_id
        original_correlation_id = complex_envelope.payload.correlation_id

        # Encrypt the payload
        complex_envelope.encrypt_payload(encryption_key)

        # Verify encryption state
        assert complex_envelope.is_encrypted is True
        assert complex_envelope.encrypted_payload is not None
        assert complex_envelope.encryption_metadata is not None

        # Decrypt and verify data integrity
        decrypted = complex_envelope.decrypt_payload(encryption_key)
        assert decrypted.event_type == original_event_type
        assert decrypted.node_id == original_node_id
        assert decrypted.correlation_id == original_correlation_id

    def test_encrypt_updates_content_hash(self, sample_envelope, encryption_key):
        """Test that encryption updates the content hash."""
        original_hash = sample_envelope.content_hash

        sample_envelope.encrypt_payload(encryption_key)

        # Content hash should be updated after encryption
        assert sample_envelope.content_hash != original_hash


@pytest.mark.unit
class TestDecryptWrongKey:
    """Test decryption with wrong key scenarios."""

    def test_decrypt_with_wrong_key_raises_security_violation_error(
        self, sample_envelope, encryption_key, different_encryption_key
    ):
        """Test that decryption with wrong key raises SECURITY_VIOLATION error.

        AES-256-GCM uses authenticated encryption, so a wrong key will cause
        the authentication tag verification to fail, which is detected as a
        potential security violation (tampering or wrong key).
        """
        # Encrypt with key1
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Attempt to decrypt with different key should raise security error
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(different_encryption_key)

        # Should be a security violation error
        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        assert (
            "authentication tag" in str(exc_info.value.message).lower()
            or "wrong key" in str(exc_info.value.message).lower()
        )


@pytest.mark.unit
class TestEncryptionMetadataPopulated:
    """Test that encryption metadata is correctly populated."""

    def test_encryption_metadata_algorithm_is_aes_256_gcm(
        self, sample_envelope, encryption_key
    ):
        """Test that encryption metadata algorithm field is set to AES-256-GCM."""
        sample_envelope.encrypt_payload(encryption_key)

        assert sample_envelope.encryption_metadata is not None
        assert sample_envelope.encryption_metadata.algorithm == "AES-256-GCM"

    def test_encryption_metadata_iv_is_valid_base64(
        self, sample_envelope, encryption_key
    ):
        """Test that encryption metadata IV is valid base64."""
        sample_envelope.encrypt_payload(encryption_key)

        assert sample_envelope.encryption_metadata is not None
        iv = sample_envelope.encryption_metadata.iv

        # Verify IV is valid base64
        try:
            decoded_iv = base64.b64decode(iv)
            # AES-GCM standard IV is 12 bytes
            assert len(decoded_iv) == 12
        except Exception as e:
            pytest.fail(f"IV is not valid base64: {e}")

    def test_encryption_metadata_auth_tag_is_valid_base64(
        self, sample_envelope, encryption_key
    ):
        """Test that encryption metadata auth tag is valid base64."""
        sample_envelope.encrypt_payload(encryption_key)

        assert sample_envelope.encryption_metadata is not None
        auth_tag = sample_envelope.encryption_metadata.auth_tag

        # Verify auth_tag is valid base64
        try:
            decoded_tag = base64.b64decode(auth_tag)
            # AES-GCM standard auth tag is 16 bytes
            assert len(decoded_tag) == 16
        except Exception as e:
            pytest.fail(f"auth_tag is not valid base64: {e}")

    def test_encryption_metadata_key_id_is_uuid(self, sample_envelope, encryption_key):
        """Test that encryption metadata key_id is a valid UUID."""
        from uuid import UUID

        sample_envelope.encrypt_payload(encryption_key)

        assert sample_envelope.encryption_metadata is not None
        key_id = sample_envelope.encryption_metadata.key_id

        # Verify key_id is a valid UUID
        assert isinstance(key_id, UUID)
        # Verify it's not a nil UUID
        assert key_id != UUID("00000000-0000-0000-0000-000000000000")

    def test_encryption_metadata_has_all_required_fields_populated(
        self, sample_envelope, encryption_key
    ):
        """Test that all required encryption metadata fields are populated after encryption.

        Required fields: algorithm, key_id, iv, auth_tag.
        Optional fields: encrypted_key (None for symmetric), recipient_keys (empty dict).
        """
        sample_envelope.encrypt_payload(encryption_key)

        metadata = sample_envelope.encryption_metadata
        assert metadata is not None

        # All required fields should be present
        assert metadata.algorithm is not None
        assert metadata.key_id is not None
        assert metadata.iv is not None
        assert metadata.auth_tag is not None

        # Optional fields should have defaults
        assert metadata.encrypted_key is None  # Only for asymmetric encryption
        assert metadata.recipient_keys == {}  # Empty dict by default


@pytest.mark.unit
class TestEncryptionDeterminism:
    """Test encryption randomness and security properties."""

    def test_encryption_of_same_payload_produces_different_ciphertext_each_time(
        self, sample_payload, sample_node_id, encryption_key
    ):
        """Test that encrypting the same payload twice produces different ciphertext.

        This is a critical security property: identical plaintexts should not produce
        identical ciphertexts. This is achieved through:
        - Random IV (nonce) generated for each encryption
        - Random key_id used as salt for PBKDF2 key derivation
        """
        route_spec = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")

        # Create two identical envelopes
        envelope1 = ModelSecureEventEnvelope(
            payload=sample_payload,
            route_spec=route_spec,
            source_node_id=sample_node_id,
            content_hash="a" * 64,
        )

        # Need to create a new payload with same data to avoid sharing
        payload2 = ModelOnexEvent(
            event_type=sample_payload.event_type,
            node_id=sample_payload.node_id,
            timestamp=sample_payload.timestamp,
            event_id=sample_payload.event_id,
        )
        envelope2 = ModelSecureEventEnvelope(
            payload=payload2,
            route_spec=route_spec,
            source_node_id=sample_node_id,
            content_hash="a" * 64,
        )

        # Encrypt both
        envelope1.encrypt_payload(encryption_key)
        envelope2.encrypt_payload(encryption_key)

        # Ciphertext should be different (due to random IV)
        assert envelope1.encrypted_payload != envelope2.encrypted_payload

        # IVs should be different
        assert envelope1.encryption_metadata.iv != envelope2.encryption_metadata.iv

        # Key IDs should be different (used as salt)
        assert (
            envelope1.encryption_metadata.key_id != envelope2.encryption_metadata.key_id
        )

    def test_iv_is_unique_per_encryption(
        self, sample_payload, sample_node_id, encryption_key
    ):
        """Test that each encryption uses a unique IV."""
        ivs = set()

        for _ in range(5):
            route_spec = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")
            envelope = ModelSecureEventEnvelope(
                payload=sample_payload,
                route_spec=route_spec,
                source_node_id=sample_node_id,
                content_hash="a" * 64,
            )
            envelope.encrypt_payload(encryption_key)
            ivs.add(envelope.encryption_metadata.iv)

        # All IVs should be unique
        assert len(ivs) == 5


@pytest.mark.unit
class TestCreateSecureEncrypted:
    """Test the create_secure_encrypted class method."""

    def test_create_secure_encrypted_returns_encrypted_envelope_with_valid_routing(
        self, sample_payload, sample_node_id, encryption_key
    ):
        """Test that the factory method creates an already-encrypted envelope with routing.

        The create_secure_encrypted factory method combines envelope creation and
        encryption in a single operation for convenience and atomicity.
        """
        destination = f"node://{uuid4()}"

        envelope = ModelSecureEventEnvelope.create_secure_encrypted(
            payload=sample_payload,
            destination=destination,
            source_node_id=sample_node_id,
            encryption_key=encryption_key,
            content_hash="a" * 64,  # Required field
        )

        # Verify envelope is encrypted
        assert envelope.is_encrypted is True
        assert envelope.encrypted_payload is not None
        assert envelope.encryption_metadata is not None
        assert envelope.encryption_metadata.algorithm == "AES-256-GCM"

        # Verify routing
        assert envelope.route_spec.final_destination == destination
        assert envelope.source_node_id == sample_node_id

    def test_create_secure_encrypted_with_authorized_roles_sets_access_control(
        self, sample_payload, sample_node_id, encryption_key
    ):
        """Test that the factory method preserves authorized_roles for access control.

        The authorized_roles field controls which roles can access the decrypted
        payload, providing an additional layer of authorization beyond encryption.
        """
        destination = f"node://{uuid4()}"

        envelope = ModelSecureEventEnvelope.create_secure_encrypted(
            payload=sample_payload,
            destination=destination,
            source_node_id=sample_node_id,
            encryption_key=encryption_key,
            authorized_roles=["admin", "operator"],
            content_hash="a" * 64,  # Required field
        )

        assert envelope.is_encrypted is True
        assert envelope.authorized_roles == ["admin", "operator"]


@pytest.mark.unit
class TestEncryptionEdgeCases:
    """Test edge cases for encryption."""

    def test_encrypt_payload_with_empty_key_succeeds_with_pbkdf2_derivation(
        self, sample_envelope
    ):
        """Test that encryption with an empty key succeeds due to PBKDF2 key derivation.

        Edge Case: Empty string as encryption key

        Why this behavior is expected:
        - PBKDF2-HMAC-SHA256 key derivation function accepts any byte string as input,
          including empty strings, and will derive a cryptographically secure 256-bit key
        - The derived key is combined with a random salt (key_id UUID), ensuring unique
          keys even when the same passphrase is used multiple times
        - This test verifies the implementation doesn't crash or reject empty input

        Security Note:
        - While technically valid, empty keys should NOT be used in production as they
          provide minimal entropy before key derivation
        - The key derivation function (PBKDF2 with 600,000 iterations per OWASP 2023
          guidelines) adds computational cost but cannot compensate for zero-entropy
          input against targeted attacks
        - Production systems should enforce minimum key length policies at the application
          layer, not within the encryption primitive itself
        """
        sample_envelope.encrypt_payload("")

        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encrypted_payload is not None

    def test_encrypt_payload_with_unicode_key_succeeds(self, sample_envelope):
        """Test that encryption succeeds with unicode characters in the key."""
        unicode_key = "test-key-with-unicode-\u00e9\u00e8\u00ea\u4e2d\u6587"

        sample_envelope.encrypt_payload(unicode_key)

        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encrypted_payload is not None

    def test_encrypt_payload_with_very_long_key_succeeds(self, sample_envelope):
        """Test that encryption succeeds with a very long key (10,000 characters)."""
        long_key = "a" * 10000

        sample_envelope.encrypt_payload(long_key)

        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encrypted_payload is not None

    def test_encrypt_payload_with_special_characters_key_succeeds(
        self, sample_envelope
    ):
        """Test that encryption succeeds with special characters in the key."""
        special_key = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

        sample_envelope.encrypt_payload(special_key)

        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encrypted_payload is not None


@pytest.mark.unit
class TestAADFunctionality:
    """Test Additional Authenticated Data (AAD) functionality for ciphertext transplantation prevention."""

    def test_aad_hash_is_populated_after_encryption(
        self, sample_envelope, encryption_key
    ):
        """Test that AAD hash is populated in encryption metadata."""
        sample_envelope.encrypt_payload(encryption_key)

        assert sample_envelope.encryption_metadata is not None
        assert sample_envelope.encryption_metadata.aad_hash is not None
        # AAD hash should be a valid SHA-256 hex string (64 characters)
        assert len(sample_envelope.encryption_metadata.aad_hash) == 64

    def test_aad_hash_is_deterministic(self, sample_envelope, encryption_key):
        """Test that AAD hash is deterministic for the same envelope."""
        # Encrypt the envelope
        sample_envelope.encrypt_payload(encryption_key)
        aad_hash = sample_envelope.encryption_metadata.aad_hash

        # Create the AAD manually and verify hash matches
        aad = sample_envelope._create_encryption_aad()
        expected_hash = hashlib.sha256(aad).hexdigest()

        assert aad_hash == expected_hash

    def test_aad_contains_envelope_identity(self, sample_envelope, encryption_key):
        """Test that AAD contains envelope identity fields."""
        aad = sample_envelope._create_encryption_aad()
        aad_string = aad.decode("utf-8")

        # AAD should contain envelope_id, source_node_id, and timestamp
        assert str(sample_envelope.envelope_id) in aad_string
        assert str(sample_envelope.source_node_id) in aad_string
        assert sample_envelope.envelope_timestamp.isoformat() in aad_string

    def test_modified_envelope_id_fails_decryption(
        self, sample_envelope, encryption_key
    ):
        """Test that modifying envelope_id after encryption causes decryption to fail."""
        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Tamper with envelope_id (simulate ciphertext transplantation)
        original_envelope_id = sample_envelope.envelope_id
        sample_envelope.envelope_id = uuid4()  # Different UUID
        assert sample_envelope.envelope_id != original_envelope_id

        # Decryption should fail due to AAD mismatch
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        assert "transplantation" in str(exc_info.value.message).lower()

    def test_modified_source_node_id_fails_decryption(
        self, sample_envelope, encryption_key
    ):
        """Test that modifying source_node_id after encryption causes decryption to fail."""
        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Tamper with source_node_id
        original_source_node_id = sample_envelope.source_node_id
        sample_envelope.source_node_id = uuid4()  # Different UUID
        assert sample_envelope.source_node_id != original_source_node_id

        # Decryption should fail due to AAD mismatch
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        assert "transplantation" in str(exc_info.value.message).lower()

    def test_modified_timestamp_fails_decryption(self, sample_envelope, encryption_key):
        """Test that modifying envelope_timestamp after encryption causes decryption to fail."""
        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True

        # Tamper with timestamp
        original_timestamp = sample_envelope.envelope_timestamp
        sample_envelope.envelope_timestamp = original_timestamp + timedelta(seconds=1)
        assert sample_envelope.envelope_timestamp != original_timestamp

        # Decryption should fail due to AAD mismatch
        with pytest.raises(ModelOnexError) as exc_info:
            sample_envelope.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
        assert "transplantation" in str(exc_info.value.message).lower()

    def test_unmodified_envelope_decrypts_successfully(
        self, sample_envelope, encryption_key
    ):
        """Test that an unmodified envelope decrypts successfully with AAD verification."""
        # Store original values
        original_event_type = sample_envelope.payload.event_type
        original_node_id = sample_envelope.payload.node_id

        # Encrypt the payload
        sample_envelope.encrypt_payload(encryption_key)
        assert sample_envelope.is_encrypted is True
        assert sample_envelope.encryption_metadata.aad_hash is not None

        # Decrypt without modifying envelope
        decrypted_payload = sample_envelope.decrypt_payload(encryption_key)

        # Verify data integrity
        assert decrypted_payload.event_type == original_event_type
        assert decrypted_payload.node_id == original_node_id

    def test_ciphertext_transplantation_attack_prevented(
        self, sample_payload, sample_node_id, encryption_key
    ):
        """Test that moving ciphertext between envelopes is detected and rejected."""
        # Create two different envelopes
        route_spec1 = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")
        route_spec2 = ModelRouteSpec.create_direct_route(f"node://{uuid4()}")

        envelope1 = ModelSecureEventEnvelope(
            payload=sample_payload,
            route_spec=route_spec1,
            source_node_id=sample_node_id,
            content_hash="a" * 64,
        )

        envelope2 = ModelSecureEventEnvelope(
            payload=sample_payload,
            route_spec=route_spec2,
            source_node_id=uuid4(),  # Different source node
            content_hash="b" * 64,
        )

        # Encrypt envelope1
        envelope1.encrypt_payload(encryption_key)

        # Attempt to transplant ciphertext to envelope2
        envelope2.encrypted_payload = envelope1.encrypted_payload
        envelope2.encryption_metadata = envelope1.encryption_metadata
        envelope2.is_encrypted = True

        # Decryption of envelope2 should fail (ciphertext was encrypted for envelope1)
        with pytest.raises(ModelOnexError) as exc_info:
            envelope2.decrypt_payload(encryption_key)

        assert exc_info.value.error_code == EnumCoreErrorCode.SECURITY_VIOLATION
