# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceCapabilityTokenVerifier.

Tests cover:
- Valid token verification (happy path)
- Expired token rejection
- Future issued_at rejection (clock skew)
- Invalid signature rejection
- Capability mismatch rejection
- Unknown issuer domain rejection
- Issuer key mismatch with trust root
- Invalid base64 in issuer_public_key
- Integration: tiered resolver uses token verification for non-local tiers

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import (
    generate_keypair,
    sign_base64,
)
from omnibase_core.enums.enum_proof_type import EnumProofType
from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)

# Import ModelHealthStatus FIRST to avoid circular import issues.
from omnibase_core.models.health.model_health_status import (
    ModelHealthStatus,  # noqa: F401 - imported for forward reference resolution
)
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)
from omnibase_core.services.service_capability_token_verifier import (
    ServiceCapabilityTokenVerifier,
)
from omnibase_core.services.service_tiered_resolver import ServiceTieredResolver

# =============================================================================
# Mock Implementations
# =============================================================================


class MockMultiKeyProvider:
    """Mock implementation of ProtocolMultiKeyProvider for testing."""

    def __init__(
        self,
        domain_keys: dict[str, bytes] | None = None,
        node_keys: dict[str, bytes] | None = None,
    ) -> None:
        self._domain_keys = domain_keys or {}
        self._node_keys = node_keys or {}

    def get_domain_trust_root(self, domain_id: str) -> bytes | None:
        return self._domain_keys.get(domain_id)

    def get_node_identity_key(self, node_id: str) -> bytes | None:
        return self._node_keys.get(node_id)


class MockProviderRegistry:
    """Mock implementation of ProtocolProviderRegistry for testing."""

    def __init__(self, providers: list[Any] | None = None) -> None:
        self.providers: list[Any] = providers or []

    def get_providers_for_capability(self, capability: str) -> list[Any]:
        return [p for p in self.providers if capability in p.capabilities]


# =============================================================================
# Fixtures
# =============================================================================


def _make_signed_token(
    keypair: Any,
    capability: str = "database.relational",
    issuer_domain: str = "org.omninode",
    subject_node_id: str = "node.compute.text-processor",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    extra_capabilities: list[str] | None = None,
) -> ModelCapabilityToken:
    """Create a properly signed capability token for testing."""
    now = datetime.now(UTC)
    _issued_at = issued_at or now
    _expires_at = expires_at or (now + timedelta(hours=1))

    capabilities = [capability]
    if extra_capabilities:
        capabilities.extend(extra_capabilities)

    token_id = uuid4()
    issuer_public_key_b64 = base64.urlsafe_b64encode(keypair.public_key_bytes).decode(
        "ascii"
    )

    # Build the signing payload (must match _build_signing_payload in verifier)
    payload = {
        "token_id": str(token_id),
        "subject_node_id": subject_node_id,
        "issuer_domain": issuer_domain,
        "capabilities": sorted(capabilities),
        "issued_at": _issued_at.isoformat(),
        "expires_at": _expires_at.isoformat(),
        "issuer_public_key": issuer_public_key_b64,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = sign_base64(keypair.private_key_bytes, canonical.encode("utf-8"))

    return ModelCapabilityToken(
        token_id=token_id,
        subject_node_id=subject_node_id,
        issuer_domain=issuer_domain,
        capabilities=capabilities,
        issued_at=_issued_at,
        expires_at=_expires_at,
        issuer_public_key=issuer_public_key_b64,
        signature=signature,
    )


def _make_trust_domain(
    domain_id: str,
    tier: EnumResolutionTier,
    allowed_capabilities: list[str] | None = None,
    policy_bundle_hash: str = "sha256:test-policy-hash",
) -> ModelTrustDomain:
    return ModelTrustDomain(
        domain_id=domain_id,
        tier=tier,
        trust_root_public_key="dGVzdC1wdWJsaWMta2V5",
        allowed_capabilities=allowed_capabilities or [],
        policy_bundle_hash=policy_bundle_hash,
    )


def _make_dependency(
    alias: str = "db",
    capability: str = "database.relational",
) -> ModelCapabilityDependency:
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
    )


def _make_provider(
    capability: str,
) -> ModelProviderDescriptor:
    return ModelProviderDescriptor(
        provider_id=uuid4(),
        capabilities=[capability],
        adapter="test.adapters.TestAdapter",
        connection_ref="env://TEST_DSN",
        attributes={},
    )


# =============================================================================
# Tests: ServiceCapabilityTokenVerifier
# =============================================================================


@pytest.mark.unit
class TestTokenVerifierHappyPath:
    """Verify that valid tokens pass all verification checks."""

    def test_valid_token_verifies(self) -> None:
        """A properly signed, non-expired token with matching capability passes."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)
        token = _make_signed_token(keypair)

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is True
        assert proof.proof_type == EnumProofType.CAPABILITY_ATTESTED
        assert proof.token is not None
        assert proof.token.token_id == token.token_id
        assert proof.verified_at is not None
        assert "verified" in proof.verification_notes.lower()

    def test_valid_token_with_multiple_capabilities(self) -> None:
        """Token with multiple capabilities can be verified for any of them."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)
        token = _make_signed_token(
            keypair,
            capability="database.relational",
            extra_capabilities=["cache.redis", "messaging.kafka"],
        )

        # Verify for each capability
        for cap in ["database.relational", "cache.redis", "messaging.kafka"]:
            proof = verifier.verify_token(token, cap)
            assert proof.verified is True, f"Failed for {cap}"


@pytest.mark.unit
class TestTokenVerifierExpiration:
    """Verify that expired tokens are rejected."""

    def test_expired_token_rejected(self) -> None:
        """A token past its expires_at is rejected."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        past = datetime.now(UTC) - timedelta(hours=2)
        expired = datetime.now(UTC) - timedelta(hours=1)
        token = _make_signed_token(keypair, issued_at=past, expires_at=expired)

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        assert "expired" in proof.verification_notes.lower()

    def test_future_issued_at_rejected(self) -> None:
        """A token with issued_at in the future is rejected (clock skew)."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        future = datetime.now(UTC) + timedelta(hours=1)
        token = _make_signed_token(
            keypair,
            issued_at=future,
            expires_at=future + timedelta(hours=1),
        )

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        assert "future" in proof.verification_notes.lower()


@pytest.mark.unit
class TestTokenVerifierSignature:
    """Verify that invalid signatures are rejected."""

    def test_invalid_signature_rejected(self) -> None:
        """A token with a tampered signature is rejected."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        # Create a valid token then tamper with the signature
        token = _make_signed_token(keypair)
        tampered = ModelCapabilityToken(
            token_id=token.token_id,
            subject_node_id=token.subject_node_id,
            issuer_domain=token.issuer_domain,
            capabilities=token.capabilities,
            issued_at=token.issued_at,
            expires_at=token.expires_at,
            issuer_public_key=token.issuer_public_key,
            signature="aW52YWxpZC1zaWduYXR1cmU=",  # wrong signature
        )

        proof = verifier.verify_token(tampered, "database.relational")

        assert proof.verified is False
        assert "signature" in proof.verification_notes.lower()

    def test_wrong_key_signature_rejected(self) -> None:
        """A token signed by a different key than the trust root is rejected."""
        issuer_keypair = generate_keypair()
        different_keypair = generate_keypair()

        # Trust root uses issuer_keypair but token is signed by different_keypair
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": issuer_keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        # Token signed with different key but claims issuer's public key
        token = _make_signed_token(different_keypair, issuer_domain="org.omninode")

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        assert (
            "trust root" in proof.verification_notes.lower()
            or "key" in proof.verification_notes.lower()
        )


@pytest.mark.unit
class TestTokenVerifierCapabilityMatch:
    """Verify that capability mismatches are rejected."""

    def test_capability_mismatch_rejected(self) -> None:
        """A token that doesn't attest the requested capability is rejected."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)
        token = _make_signed_token(keypair, capability="cache.redis")

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        assert "database.relational" in proof.verification_notes
        assert "cache.redis" in proof.verification_notes


@pytest.mark.unit
class TestTokenVerifierTrustRoot:
    """Verify trust root lookup failures."""

    def test_unknown_domain_rejected(self) -> None:
        """A token from an unknown domain (no trust root) is rejected."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(domain_keys={})  # no keys
        verifier = ServiceCapabilityTokenVerifier(key_provider)
        token = _make_signed_token(keypair)

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        assert "trust root" in proof.verification_notes.lower()

    def test_issuer_key_mismatch_with_trust_root(self) -> None:
        """Token's issuer key does not match the domain's trust root."""
        real_keypair = generate_keypair()
        fake_keypair = generate_keypair()

        # Trust root is real_keypair, but token claims fake_keypair as issuer
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": real_keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        # Sign with fake key and set fake key as issuer
        token = _make_signed_token(fake_keypair, issuer_domain="org.omninode")

        proof = verifier.verify_token(token, "database.relational")

        assert proof.verified is False
        # The issuer key in the token (fake) != trust root (real)
        assert (
            "trust root" in proof.verification_notes.lower()
            or "key" in proof.verification_notes.lower()
        )


@pytest.mark.unit
class TestTokenVerifierEdgeCases:
    """Edge cases for token verification."""

    def test_invalid_base64_issuer_key(self) -> None:
        """Token with invalid base64 in issuer_public_key is rejected."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        # Create token with garbage base64
        now = datetime.now(UTC)
        token = ModelCapabilityToken(
            token_id=uuid4(),
            subject_node_id="node.test",
            issuer_domain="org.omninode",
            capabilities=["database.relational"],
            issued_at=now,
            expires_at=now + timedelta(hours=1),
            issuer_public_key="not!valid!base64!!!",
            signature="dGVzdA==",
        )

        proof = verifier.verify_token(token, "database.relational")

        # Should fail at base64 decode or key mismatch
        assert proof.verified is False

    def test_repr_and_str(self) -> None:
        """Verify __repr__ and __str__ work."""
        key_provider = MockMultiKeyProvider()
        verifier = ServiceCapabilityTokenVerifier(key_provider)

        assert "ServiceCapabilityTokenVerifier" in repr(verifier)
        assert str(verifier) == "ServiceCapabilityTokenVerifier"


# =============================================================================
# Tests: Integration with ServiceTieredResolver
# =============================================================================


@pytest.mark.unit
class TestTieredResolverTokenIntegration:
    """Verify that ServiceTieredResolver uses token verification for non-local tiers."""

    def test_non_local_tier_with_valid_token_resolves(self) -> None:
        """ORG_TRUSTED tier with a valid capability token resolves successfully."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        token_verifier = ServiceCapabilityTokenVerifier(key_provider)

        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            token_verifier=token_verifier,
        )

        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )
        dep = _make_dependency()
        token = _make_signed_token(keypair, issuer_domain="org.omninode")

        result = resolver.resolve_tiered(dep, [domain], capability_tokens=[token])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED
        assert result.structured_failure is None

    def test_non_local_tier_with_expired_token_fails(self) -> None:
        """ORG_TRUSTED tier with expired token produces attestation_invalid."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        token_verifier = ServiceCapabilityTokenVerifier(key_provider)

        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            token_verifier=token_verifier,
        )

        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )
        dep = _make_dependency()

        # Create expired token
        past = datetime.now(UTC) - timedelta(hours=2)
        expired_at = datetime.now(UTC) - timedelta(hours=1)
        token = _make_signed_token(
            keypair,
            issuer_domain="org.omninode",
            issued_at=past,
            expires_at=expired_at,
        )

        result = resolver.resolve_tiered(dep, [domain], capability_tokens=[token])

        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        # The tier attempt should show attestation_invalid
        assert len(result.tier_progression) == 1
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.ATTESTATION_INVALID
        )

    def test_non_local_tier_without_token_fails(self) -> None:
        """ORG_TRUSTED tier without any token produces attestation_invalid."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        token_verifier = ServiceCapabilityTokenVerifier(key_provider)

        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            token_verifier=token_verifier,
        )

        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )
        dep = _make_dependency()

        # Pass empty token list
        result = resolver.resolve_tiered(dep, [domain], capability_tokens=[])

        assert result.route_plan is None
        assert len(result.tier_progression) == 1
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.ATTESTATION_INVALID
        )

    def test_local_exact_skips_token_verification(self) -> None:
        """LOCAL_EXACT tier does not require token verification."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"local.default": keypair.public_key_bytes}
        )
        token_verifier = ServiceCapabilityTokenVerifier(key_provider)

        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            token_verifier=token_verifier,
        )

        domain = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
        )
        dep = _make_dependency()

        # No tokens provided - should still resolve at local_exact
        result = resolver.resolve_tiered(dep, [domain], capability_tokens=[])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT

    def test_no_verifier_skips_token_check(self) -> None:
        """Without a token_verifier, non-local tiers resolve without token check."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            # No token_verifier
        )

        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain])

        # Should resolve even without tokens (backward compatible)
        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED

    def test_fallback_from_failed_token_to_local_exact(self) -> None:
        """Token fails at ORG_TRUSTED but LOCAL_EXACT succeeds (no token needed)."""
        keypair = generate_keypair()
        key_provider = MockMultiKeyProvider(
            domain_keys={"org.omninode": keypair.public_key_bytes}
        )
        token_verifier = ServiceCapabilityTokenVerifier(key_provider)

        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
            token_verifier=token_verifier,
        )

        domain_local = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
        )
        domain_org = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )
        dep = _make_dependency()

        # Expired token for org tier
        past = datetime.now(UTC) - timedelta(hours=2)
        expired_at = datetime.now(UTC) - timedelta(hours=1)
        token = _make_signed_token(
            keypair,
            issuer_domain="org.omninode",
            issued_at=past,
            expires_at=expired_at,
        )

        result = resolver.resolve_tiered(
            dep, [domain_local, domain_org], capability_tokens=[token]
        )

        # LOCAL_EXACT should win (processed first in canonical order)
        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
