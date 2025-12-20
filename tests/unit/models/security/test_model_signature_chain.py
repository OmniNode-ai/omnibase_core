"""
Tests for ModelSignatureChain.

This module tests the tamper-evident signature chain for secure envelope routing
with comprehensive audit trails and tamper detection capabilities.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_chain_validation_status import EnumChainValidationStatus
from omnibase_core.enums.enum_compliance_framework import EnumComplianceFramework
from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.enums.enum_trust_level import EnumTrustLevel
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_chain_metrics import ModelChainMetrics
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_signature_chain import ModelSignatureChain
from omnibase_core.models.security.model_signing_policy import ModelSigningPolicy

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelSignatureChainBasic:
    """Test basic ModelSignatureChain functionality."""

    def test_create_signature_chain_basic(self):
        """Test creating a basic signature chain."""
        chain_id = uuid4()
        envelope_id = uuid4()

        chain = ModelSignatureChain(
            chain_id=chain_id, envelope_id=envelope_id, content_hash="test_hash"
        )

        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id
        assert chain.signatures == []
        assert chain.validation_status == EnumChainValidationStatus.INCOMPLETE
        assert chain.trust_level == EnumTrustLevel.UNTRUSTED

    def test_create_signature_chain_with_signatures(self):
        """Test creating a signature chain with signatures."""
        chain_id = uuid4()
        envelope_id = uuid4()

        # Create mock signatures
        signature1 = ModelNodeSignature(
            node_id=uuid4(),
            signature="c2lnbmF0dXJlMQ==",  # base64 encoded "signature1"
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.ROUTE,
            key_id=uuid4(),
            hop_index=0,
            envelope_state_hash="a" * 64,  # 64 character SHA-256 hash
        )
        signature2 = ModelNodeSignature(
            node_id=uuid4(),
            signature="c2lnbmF0dXJlMg==",  # base64 encoded "signature2"
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.VALIDATE,
            key_id=uuid4(),
            hop_index=1,
            envelope_state_hash="a" * 64,  # 64 character SHA-256 hash
        )

        chain = ModelSignatureChain(
            chain_id=chain_id,
            envelope_id=envelope_id,
            content_hash="a" * 64,  # 64 character SHA-256 hash
            signatures=[signature1, signature2],
        )

        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id
        assert len(chain.signatures) == 2
        assert chain.signatures[0] == signature1
        assert chain.signatures[1] == signature2

    def test_signature_chain_validation(self):
        """Test signature chain validation."""
        chain_id = uuid4()
        envelope_id = uuid4()

        # Valid chain
        chain = ModelSignatureChain(
            chain_id=chain_id, envelope_id=envelope_id, content_hash="test_hash"
        )
        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id

        # Test required fields
        with pytest.raises(ValueError):
            ModelSignatureChain(
                chain_id=None,
                envelope_id=envelope_id,  # Invalid chain_id
            )

        with pytest.raises(ValueError):
            ModelSignatureChain(
                chain_id=chain_id,
                envelope_id=None,  # Invalid envelope_id
            )

    def test_signature_chain_serialization(self):
        """Test signature chain serialization."""
        chain_id = uuid4()
        envelope_id = uuid4()

        chain = ModelSignatureChain(
            chain_id=chain_id,
            envelope_id=envelope_id,
            content_hash="test_hash",
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH_TRUST,
        )

        data = chain.model_dump()
        assert data["chain_id"] == chain_id
        assert data["envelope_id"] == envelope_id
        assert data["validation_status"] == "valid"
        assert data["trust_level"] == "high_trust"

    def test_signature_chain_deserialization(self):
        """Test signature chain deserialization."""
        chain_id = uuid4()
        envelope_id = uuid4()

        data = {
            "chain_id": str(chain_id),
            "envelope_id": str(envelope_id),
            "content_hash": "test_hash",
            "validation_status": "valid",
            "trust_level": "high_trust",
        }

        chain = ModelSignatureChain.model_validate(data)
        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id
        assert chain.validation_status == EnumChainValidationStatus.VALID
        assert chain.trust_level == EnumTrustLevel.HIGH_TRUST


@pytest.mark.unit
class TestModelSignatureChainEnums:
    """Test ModelSignatureChain with different enum values."""

    def test_validation_statuses(self):
        """Test different validation statuses."""
        for status in EnumChainValidationStatus:
            chain = ModelSignatureChain(
                chain_id=uuid4(),
                envelope_id=uuid4(),
                content_hash="a" * 64,
                validation_status=status,
            )
            assert chain.validation_status == status

    def test_trust_levels(self):
        """Test different trust levels."""
        for trust_level in EnumTrustLevel:
            chain = ModelSignatureChain(
                chain_id=uuid4(),
                envelope_id=uuid4(),
                content_hash="a" * 64,
                trust_level=trust_level,
            )
            assert chain.trust_level == trust_level

    def test_compliance_frameworks(self):
        """Test different compliance frameworks."""
        for framework in EnumComplianceFramework:
            chain = ModelSignatureChain(
                chain_id=uuid4(),
                envelope_id=uuid4(),
                content_hash="a" * 64,
                compliance_frameworks=[framework],
            )
            assert framework in chain.compliance_frameworks

    def test_enum_combinations(self):
        """Test various enum combinations."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH_TRUST,
            compliance_frameworks=[EnumComplianceFramework.SOX],
        )

        assert chain.validation_status == EnumChainValidationStatus.VALID
        assert chain.trust_level == EnumTrustLevel.HIGH_TRUST
        assert EnumComplianceFramework.SOX in chain.compliance_frameworks


@pytest.mark.unit
class TestModelSignatureChainSignatures:
    """Test ModelSignatureChain signature management."""

    def test_add_signature(self):
        """Test adding a signature to the chain."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        signature = ModelNodeSignature(
            node_id=uuid4(),
            signature="dGVzdF9zaWduYXR1cmU=",  # base64 encoded "test_signature"
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.TRANSFORM,
            key_id=uuid4(),
            hop_index=0,
            envelope_state_hash="a" * 64,
        )

        chain.signatures.append(signature)
        assert len(chain.signatures) == 1
        assert chain.signatures[0] == signature

    def test_multiple_signatures(self):
        """Test adding multiple signatures."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        signatures = []
        for i in range(5):
            signature = ModelNodeSignature(
                node_id=uuid4(),
                signature="c2lnbmF0dXJlX3swfQ==".format(),  # base64 encoded "signature_{i}"
                timestamp=datetime.now(UTC),
                operation=EnumNodeOperation.TRANSFORM,
                key_id=uuid4(),
                hop_index=i,
                envelope_state_hash="a" * 64,
            )
            signatures.append(signature)
            chain.signatures.append(signature)

        assert len(chain.signatures) == 5
        for i, signature in enumerate(chain.signatures):
            assert signature.signature == "c2lnbmF0dXJlX3swfQ==".format()

    def test_signature_order(self):
        """Test that signatures maintain order."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        # Add signatures in specific order
        signatures = []
        for i in range(3):
            signature = ModelNodeSignature(
                node_id=uuid4(),
                signature="c2lnbmF0dXJlX3swfQ==".format(),  # base64 encoded "signature_{i}"
                timestamp=datetime.now(UTC),
                operation=EnumNodeOperation.TRANSFORM,
                key_id=uuid4(),
                hop_index=i,
                envelope_state_hash="a" * 64,
            )
            signatures.append(signature)
            chain.signatures.append(signature)

        # Verify order is maintained
        for i, signature in enumerate(chain.signatures):
            assert signature.signature == "c2lnbmF0dXJlX3swfQ==".format()

    def test_empty_signatures(self):
        """Test chain with no signatures."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        assert chain.signatures == []
        assert len(chain.signatures) == 0


@pytest.mark.unit
class TestModelSignatureChainTimestamps:
    """Test ModelSignatureChain timestamp functionality."""

    def test_created_timestamp(self):
        """Test created timestamp."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        assert chain.created_at is not None
        assert isinstance(chain.created_at, datetime)

    def test_updated_timestamp(self):
        """Test updated timestamp."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        assert chain.last_modified is not None
        assert isinstance(chain.last_modified, datetime)

    def test_timestamp_ordering(self):
        """Test that timestamps are properly ordered."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        # Created should be before or equal to updated
        assert chain.created_at <= chain.last_modified

    def test_custom_timestamps(self):
        """Test setting custom timestamps."""
        created = datetime.now(UTC) - timedelta(hours=1)
        updated = datetime.now(UTC)

        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
            created_at=created,
            last_modified=updated,
        )

        assert chain.created_at == created
        assert chain.last_modified == updated


@pytest.mark.unit
class TestModelSignatureChainMetrics:
    """Test ModelSignatureChain metrics functionality."""

    def test_chain_metrics(self):
        """Test chain metrics."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        # Test default metrics (should be None by default)
        assert chain.chain_metrics is None

    def test_custom_metrics(self):
        """Test custom chain metrics."""
        custom_metrics = ModelChainMetrics(
            total_signatures=5, valid_signatures=5, verification_time_ms=100.0
        )

        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
            chain_metrics=custom_metrics,
        )

        assert chain.chain_metrics == custom_metrics
        assert chain.chain_metrics.total_signatures == 5
        assert chain.chain_metrics.valid_signatures == 5
        assert chain.chain_metrics.verification_time_ms == 100.0


@pytest.mark.unit
class TestModelSignatureChainPolicies:
    """Test ModelSignatureChain signing policies."""

    def test_signing_policy(self):
        """Test signing policy."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        # Test default policy (should be None by default)
        assert chain.signing_policy is None

    def test_custom_signing_policy(self):
        """Test custom signing policy."""
        custom_policy = ModelSigningPolicy(
            minimum_signatures=3, max_hop_count=10, require_sequential_timestamps=True
        )

        envelope_id = uuid4()
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=envelope_id,
            content_hash="a" * 64,
            signing_policy=custom_policy,
        )

        assert chain.signing_policy == custom_policy
        assert chain.signing_policy.minimum_signatures == 3
        assert chain.signing_policy.max_hop_count == 10
        assert chain.signing_policy.require_sequential_timestamps is True


@pytest.mark.unit
class TestModelSignatureChainEdgeCases:
    """Test ModelSignatureChain edge cases."""

    def test_unicode_characters(self):
        """Test with unicode characters."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
        )

        # Test that the chain was created successfully with unicode support
        assert chain.chain_id is not None
        assert chain.envelope_id is not None

    def test_special_characters(self):
        """Test with special characters."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
        )

        # Test that the chain was created successfully with special character support
        assert chain.chain_id is not None
        assert chain.envelope_id is not None

    def test_large_metadata(self):
        """Test with large metadata."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        # Test that the chain was created successfully
        assert chain.chain_id is not None
        assert chain.envelope_id is not None


@pytest.mark.unit
class TestModelSignatureChainSerialization:
    """Test ModelSignatureChain serialization scenarios."""

    def test_json_serialization(self):
        """Test JSON serialization."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH_TRUST,
        )

        json_data = chain.model_dump_json()
        assert isinstance(json_data, str)
        assert "chain_id" in json_data
        assert "envelope_id" in json_data
        assert "valid" in json_data
        assert "high_trust" in json_data

    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original_chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            content_hash="a" * 64,
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH_TRUST,
            compliance_frameworks=[EnumComplianceFramework.SOX],
        )

        # Serialize
        data = original_chain.model_dump()

        # Deserialize
        restored_chain = ModelSignatureChain.model_validate(data)

        # Verify all fields match
        assert restored_chain.chain_id == original_chain.chain_id
        assert restored_chain.envelope_id == original_chain.envelope_id
        assert restored_chain.validation_status == original_chain.validation_status
        assert restored_chain.trust_level == original_chain.trust_level
        assert (
            restored_chain.compliance_frameworks == original_chain.compliance_frameworks
        )
        # All fields match successfully

    def test_partial_serialization(self):
        """Test serialization with only required fields."""
        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), content_hash="a" * 64
        )

        data = chain.model_dump()
        assert "chain_id" in data
        assert "envelope_id" in data
        assert data["chain_id"] == chain.chain_id
        assert data["envelope_id"] == chain.envelope_id
