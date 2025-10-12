"""
Tests for ModelSignatureChain.

This module tests the tamper-evident signature chain for secure envelope routing
with comprehensive audit trails and tamper detection capabilities.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_chain_validation_status import EnumChainValidationStatus
from omnibase_core.enums.enum_compliance_framework import EnumComplianceFramework
from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.enums.enum_trust_level import EnumTrustLevel
from omnibase_core.models.security.model_chain_metrics import ModelChainMetrics
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_signature_chain import ModelSignatureChain
from omnibase_core.models.security.model_signing_policy import ModelSigningPolicy


class TestModelSignatureChainBasic:
    """Test basic ModelSignatureChain functionality."""

    def test_create_signature_chain_basic(self):
        """Test creating a basic signature chain."""
        chain_id = uuid4()
        envelope_id = uuid4()

        chain = ModelSignatureChain(chain_id=chain_id, envelope_id=envelope_id)

        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id
        assert chain.signatures == []
        assert chain.validation_status == EnumChainValidationStatus.PENDING
        assert chain.trust_level == EnumTrustLevel.UNKNOWN

    def test_create_signature_chain_with_signatures(self):
        """Test creating a signature chain with signatures."""
        chain_id = uuid4()
        envelope_id = uuid4()

        # Create mock signatures
        signature1 = ModelNodeSignature(
            node_id=uuid4(),
            signature="signature1",
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.PROCESS,
        )
        signature2 = ModelNodeSignature(
            node_id=uuid4(),
            signature="signature2",
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.VALIDATE,
        )

        chain = ModelSignatureChain(
            chain_id=chain_id,
            envelope_id=envelope_id,
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
        chain = ModelSignatureChain(chain_id=chain_id, envelope_id=envelope_id)
        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id

        # Test required fields
        with pytest.raises(ValueError):
            ModelSignatureChain(
                chain_id=None, envelope_id=envelope_id  # Invalid chain_id
            )

        with pytest.raises(ValueError):
            ModelSignatureChain(
                chain_id=chain_id, envelope_id=None  # Invalid envelope_id
            )

    def test_signature_chain_serialization(self):
        """Test signature chain serialization."""
        chain_id = uuid4()
        envelope_id = uuid4()

        chain = ModelSignatureChain(
            chain_id=chain_id,
            envelope_id=envelope_id,
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH,
        )

        data = chain.model_dump()
        assert data["chain_id"] == str(chain_id)
        assert data["envelope_id"] == str(envelope_id)
        assert data["validation_status"] == "VALID"
        assert data["trust_level"] == "HIGH"

    def test_signature_chain_deserialization(self):
        """Test signature chain deserialization."""
        chain_id = uuid4()
        envelope_id = uuid4()

        data = {
            "chain_id": str(chain_id),
            "envelope_id": str(envelope_id),
            "validation_status": "VALID",
            "trust_level": "HIGH",
        }

        chain = ModelSignatureChain.model_validate(data)
        assert chain.chain_id == chain_id
        assert chain.envelope_id == envelope_id
        assert chain.validation_status == EnumChainValidationStatus.VALID
        assert chain.trust_level == EnumTrustLevel.HIGH


class TestModelSignatureChainEnums:
    """Test ModelSignatureChain with different enum values."""

    def test_validation_statuses(self):
        """Test different validation statuses."""
        for status in EnumChainValidationStatus:
            chain = ModelSignatureChain(
                chain_id=uuid4(), envelope_id=uuid4(), validation_status=status
            )
            assert chain.validation_status == status

    def test_trust_levels(self):
        """Test different trust levels."""
        for trust_level in EnumTrustLevel:
            chain = ModelSignatureChain(
                chain_id=uuid4(), envelope_id=uuid4(), trust_level=trust_level
            )
            assert chain.trust_level == trust_level

    def test_compliance_frameworks(self):
        """Test different compliance frameworks."""
        for framework in EnumComplianceFramework:
            chain = ModelSignatureChain(
                chain_id=uuid4(), envelope_id=uuid4(), compliance_framework=framework
            )
            assert chain.compliance_framework == framework

    def test_enum_combinations(self):
        """Test various enum combinations."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH,
            compliance_framework=EnumComplianceFramework.SOC2,
        )

        assert chain.validation_status == EnumChainValidationStatus.VALID
        assert chain.trust_level == EnumTrustLevel.HIGH
        assert chain.compliance_framework == EnumComplianceFramework.SOC2


class TestModelSignatureChainSignatures:
    """Test ModelSignatureChain signature management."""

    def test_add_signature(self):
        """Test adding a signature to the chain."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        signature = ModelNodeSignature(
            node_id=uuid4(),
            signature="test_signature",
            timestamp=datetime.now(UTC),
            operation=EnumNodeOperation.PROCESS,
        )

        chain.signatures.append(signature)
        assert len(chain.signatures) == 1
        assert chain.signatures[0] == signature

    def test_multiple_signatures(self):
        """Test adding multiple signatures."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        signatures = []
        for i in range(5):
            signature = ModelNodeSignature(
                node_id=uuid4(),
                signature=f"signature_{i}",
                timestamp=datetime.now(UTC),
                operation=EnumNodeOperation.PROCESS,
            )
            signatures.append(signature)
            chain.signatures.append(signature)

        assert len(chain.signatures) == 5
        for i, signature in enumerate(chain.signatures):
            assert signature.signature == f"signature_{i}"

    def test_signature_order(self):
        """Test that signatures maintain order."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        # Add signatures in specific order
        signatures = []
        for i in range(3):
            signature = ModelNodeSignature(
                node_id=uuid4(),
                signature=f"signature_{i}",
                timestamp=datetime.now(UTC),
                operation=EnumNodeOperation.PROCESS,
            )
            signatures.append(signature)
            chain.signatures.append(signature)

        # Verify order is maintained
        for i, signature in enumerate(chain.signatures):
            assert signature.signature == f"signature_{i}"

    def test_empty_signatures(self):
        """Test chain with no signatures."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        assert chain.signatures == []
        assert len(chain.signatures) == 0


class TestModelSignatureChainTimestamps:
    """Test ModelSignatureChain timestamp functionality."""

    def test_created_timestamp(self):
        """Test created timestamp."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        assert chain.created_at is not None
        assert isinstance(chain.created_at, datetime)

    def test_updated_timestamp(self):
        """Test updated timestamp."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        assert chain.updated_at is not None
        assert isinstance(chain.updated_at, datetime)

    def test_timestamp_ordering(self):
        """Test that timestamps are properly ordered."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        # Created should be before or equal to updated
        assert chain.created_at <= chain.updated_at

    def test_custom_timestamps(self):
        """Test setting custom timestamps."""
        created = datetime.now(UTC) - timedelta(hours=1)
        updated = datetime.now(UTC)

        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            created_at=created,
            updated_at=updated,
        )

        assert chain.created_at == created
        assert chain.updated_at == updated


class TestModelSignatureChainMetrics:
    """Test ModelSignatureChain metrics functionality."""

    def test_chain_metrics(self):
        """Test chain metrics."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        # Test default metrics
        assert chain.metrics is not None
        assert isinstance(chain.metrics, ModelChainMetrics)

    def test_custom_metrics(self):
        """Test custom chain metrics."""
        custom_metrics = ModelChainMetrics(
            total_signatures=5, validation_errors=0, processing_time_ms=100
        )

        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), metrics=custom_metrics
        )

        assert chain.metrics == custom_metrics
        assert chain.metrics.total_signatures == 5
        assert chain.metrics.validation_errors == 0
        assert chain.metrics.processing_time_ms == 100


class TestModelSignatureChainPolicies:
    """Test ModelSignatureChain signing policies."""

    def test_signing_policy(self):
        """Test signing policy."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        # Test default policy
        assert chain.signing_policy is not None
        assert isinstance(chain.signing_policy, ModelSigningPolicy)

    def test_custom_signing_policy(self):
        """Test custom signing policy."""
        custom_policy = ModelSigningPolicy(
            required_signatures=3, max_chain_length=10, validation_timeout_seconds=30
        )

        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=envelope_id, signing_policy=custom_policy
        )

        assert chain.signing_policy == custom_policy
        assert chain.signing_policy.required_signatures == 3
        assert chain.signing_policy.max_chain_length == 10
        assert chain.signing_policy.validation_timeout_seconds == 30


class TestModelSignatureChainEdgeCases:
    """Test ModelSignatureChain edge cases."""

    def test_unicode_characters(self):
        """Test with unicode characters."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            metadata={"description": "测试签名链", "author": "测试用户"},
        )

        assert chain.metadata["description"] == "测试签名链"
        assert chain.metadata["author"] == "测试用户"

    def test_special_characters(self):
        """Test with special characters."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            metadata={"special": "!@#$%^&*()_+-=[]{}|;':\",./<>?"},
        )

        assert chain.metadata["special"] == "!@#$%^&*()_+-=[]{}|;':\",./<>?"

    def test_large_metadata(self):
        """Test with large metadata."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}

        chain = ModelSignatureChain(
            chain_id=uuid4(), envelope_id=uuid4(), metadata=large_metadata
        )

        assert len(chain.metadata) == 100
        assert chain.metadata["key_0"] == "value_0"
        assert chain.metadata["key_99"] == "value_99"


class TestModelSignatureChainSerialization:
    """Test ModelSignatureChain serialization scenarios."""

    def test_json_serialization(self):
        """Test JSON serialization."""
        chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH,
        )

        json_data = chain.model_dump_json()
        assert isinstance(json_data, str)
        assert "chain_id" in json_data
        assert "envelope_id" in json_data
        assert "VALID" in json_data
        assert "HIGH" in json_data

    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original_chain = ModelSignatureChain(
            chain_id=uuid4(),
            envelope_id=uuid4(),
            validation_status=EnumChainValidationStatus.VALID,
            trust_level=EnumTrustLevel.HIGH,
            compliance_framework=EnumComplianceFramework.SOC2,
            metadata={"test": "value", "number": 42},
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
            restored_chain.compliance_framework == original_chain.compliance_framework
        )
        assert restored_chain.metadata == original_chain.metadata

    def test_partial_serialization(self):
        """Test serialization with only required fields."""
        chain = ModelSignatureChain(chain_id=uuid4(), envelope_id=uuid4())

        data = chain.model_dump()
        assert "chain_id" in data
        assert "envelope_id" in data
        assert data["chain_id"] == str(chain.chain_id)
        assert data["envelope_id"] == str(chain.envelope_id)
