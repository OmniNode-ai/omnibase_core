# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 3 routing models: capability tokens and resolution proofs."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_proof_type import EnumProofType
from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken
from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_capability_token(**overrides: object) -> ModelCapabilityToken:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "token_id": uuid4(),
        "subject_node_id": "node.compute.text-processor",
        "issuer_domain": "org.omninode",
        "capabilities": ["database.relational", "cache.redis"],
        "issued_at": now,
        "expires_at": now + timedelta(hours=1),
        "issuer_public_key": "dGVzdC1wdWJsaWMta2V5LWJhc2U2NA==",
        "signature": "dGVzdC1zaWduYXR1cmUtYmFzZTY0",
    }
    defaults.update(overrides)
    return ModelCapabilityToken(**defaults)  # type: ignore[arg-type]


def _make_resolution_proof(**overrides: object) -> ModelResolutionProof:
    defaults: dict[str, object] = {
        "proof_type": EnumProofType.CAPABILITY_ATTESTED,
        "verified": True,
        "verification_notes": "Token verified successfully",
    }
    defaults.update(overrides)
    return ModelResolutionProof(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# EnumProofType
# ===========================================================================


@pytest.mark.unit
class TestEnumProofType:
    """Tests for EnumProofType."""

    def test_all_values_present(self) -> None:
        assert EnumProofType.NODE_IDENTITY.value == "node_identity"
        assert EnumProofType.CAPABILITY_ATTESTED.value == "capability_attested"
        assert EnumProofType.ORG_MEMBERSHIP.value == "org_membership"
        assert EnumProofType.BUS_MEMBERSHIP.value == "bus_membership"
        assert EnumProofType.POLICY_COMPLIANCE.value == "policy_compliance"

    def test_member_count(self) -> None:
        assert len(EnumProofType) == 5

    def test_str_returns_value(self) -> None:
        assert str(EnumProofType.NODE_IDENTITY) == "node_identity"
        assert str(EnumProofType.POLICY_COMPLIANCE) == "policy_compliance"

    def test_lookup_by_value(self) -> None:
        assert EnumProofType("node_identity") is EnumProofType.NODE_IDENTITY
        assert EnumProofType("capability_attested") is EnumProofType.CAPABILITY_ATTESTED

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumProofType("nonexistent_proof")

    def test_unique_values(self) -> None:
        values = [m.value for m in EnumProofType]
        assert len(values) == len(set(values))

    def test_is_string_subclass(self) -> None:
        assert isinstance(EnumProofType.NODE_IDENTITY, str)


# ===========================================================================
# ModelCapabilityToken
# ===========================================================================


@pytest.mark.unit
class TestModelCapabilityToken:
    """Tests for ModelCapabilityToken."""

    def test_create_with_required_fields(self) -> None:
        token = _make_capability_token()
        assert token.subject_node_id == "node.compute.text-processor"
        assert token.issuer_domain == "org.omninode"
        assert len(token.capabilities) == 2
        assert "database.relational" in token.capabilities
        assert token.issuer_public_key == "dGVzdC1wdWJsaWMta2V5LWJhc2U2NA=="
        assert token.signature == "dGVzdC1zaWduYXR1cmUtYmFzZTY0"

    def test_frozen(self) -> None:
        token = _make_capability_token()
        with pytest.raises(ValidationError):
            token.subject_node_id = "other"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_capability_token(unknown_field="bad")

    def test_serialization_round_trip(self) -> None:
        token = _make_capability_token()
        data = token.model_dump()
        restored = ModelCapabilityToken.model_validate(data)
        assert restored == token

    def test_json_round_trip(self) -> None:
        token = _make_capability_token()
        json_str = token.model_dump_json()
        restored = ModelCapabilityToken.model_validate_json(json_str)
        assert restored == token

    def test_empty_subject_node_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_capability_token(subject_node_id="")

    def test_empty_issuer_domain_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_capability_token(issuer_domain="")

    def test_empty_capabilities_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_capability_token(capabilities=[])

    def test_empty_issuer_public_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_capability_token(issuer_public_key="")

    def test_empty_signature_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_capability_token(signature="")

    def test_datetime_fields_preserved(self) -> None:
        now = datetime.now(UTC)
        later = now + timedelta(hours=2)
        token = _make_capability_token(issued_at=now, expires_at=later)
        assert token.issued_at == now
        assert token.expires_at == later

    def test_single_capability(self) -> None:
        token = _make_capability_token(capabilities=["database.relational"])
        assert token.capabilities == ["database.relational"]


# ===========================================================================
# ModelResolutionProof
# ===========================================================================


@pytest.mark.unit
class TestModelResolutionProof:
    """Tests for ModelResolutionProof."""

    def test_create_successful_proof(self) -> None:
        proof = _make_resolution_proof()
        assert proof.proof_type == EnumProofType.CAPABILITY_ATTESTED
        assert proof.verified is True
        assert proof.verification_notes == "Token verified successfully"
        assert proof.token is None
        assert proof.verified_at is None

    def test_create_with_token(self) -> None:
        token = _make_capability_token()
        proof = _make_resolution_proof(
            token=token,
            verified_at=datetime.now(UTC),
        )
        assert proof.token is not None
        assert proof.token.subject_node_id == "node.compute.text-processor"
        assert proof.verified_at is not None

    def test_create_failed_proof(self) -> None:
        proof = _make_resolution_proof(
            verified=False,
            verification_notes="Token expired",
        )
        assert proof.verified is False
        assert proof.verification_notes == "Token expired"

    def test_frozen(self) -> None:
        proof = _make_resolution_proof()
        with pytest.raises(ValidationError):
            proof.verified = False  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_resolution_proof(extra="bad")

    def test_serialization_round_trip(self) -> None:
        token = _make_capability_token()
        proof = _make_resolution_proof(
            token=token,
            verified_at=datetime.now(UTC),
        )
        data = proof.model_dump()
        restored = ModelResolutionProof.model_validate(data)
        assert restored == proof

    def test_json_round_trip(self) -> None:
        proof = _make_resolution_proof()
        json_str = proof.model_dump_json()
        restored = ModelResolutionProof.model_validate_json(json_str)
        assert restored == proof

    def test_all_proof_types(self) -> None:
        """Each proof type can be used in a ModelResolutionProof."""
        for proof_type in EnumProofType:
            proof = _make_resolution_proof(proof_type=proof_type)
            assert proof.proof_type == proof_type

    def test_enum_string_deserialization(self) -> None:
        """Proof type accepts string values for deserialization."""
        proof = ModelResolutionProof.model_validate(
            {
                "proof_type": "node_identity",
                "verified": True,
                "verification_notes": "Identity confirmed",
            }
        )
        assert proof.proof_type == EnumProofType.NODE_IDENTITY

    def test_invalid_proof_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelResolutionProof.model_validate(
                {
                    "proof_type": "nonexistent",
                    "verified": True,
                    "verification_notes": "test",
                }
            )

    def test_json_round_trip_with_nested_token(self) -> None:
        """Full JSON round-trip including nested ModelCapabilityToken."""
        token = _make_capability_token()
        proof = _make_resolution_proof(
            proof_type=EnumProofType.CAPABILITY_ATTESTED,
            verified=True,
            verification_notes="Full chain verified",
            token=token,
            verified_at=datetime.now(UTC),
        )
        json_str = proof.model_dump_json()
        restored = ModelResolutionProof.model_validate_json(json_str)
        assert restored == proof
        assert restored.token is not None
        assert restored.token.token_id == token.token_id
