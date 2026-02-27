# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Capability token verification service.

Verifies capability tokens by checking expiration, retrieving the issuer's
trust root key, verifying the Ed25519 signature, and confirming that the
token attests the requested capability. Returns a ``ModelResolutionProof``
recording the verification outcome.

Algorithm:
    1. Check token expiration against current UTC time.
    2. Retrieve issuer trust root key via ``ProtocolMultiKeyProvider``.
    3. Decode the issuer public key from the token.
    4. Verify that the token's issuer key matches the trust root.
    5. Verify the Ed25519 signature over the token payload.
    6. Confirm the requested capability is in the token's capability list.
    7. Return a ``ModelResolutionProof`` with the verification outcome.

All failure paths produce a proof with ``verified=False`` and descriptive
notes -- no exceptions are raised for verification failures.

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

__all__ = ["ServiceCapabilityTokenVerifier"]

import base64
import json
import logging
from datetime import UTC, datetime

from omnibase_core.crypto.crypto_ed25519_signer import verify_base64
from omnibase_core.enums.enum_proof_type import EnumProofType
from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken
from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof
from omnibase_core.protocols.crypto.protocol_multi_key_provider import (
    ProtocolMultiKeyProvider,
)

logger = logging.getLogger(__name__)


def _build_signing_payload(token: ModelCapabilityToken) -> bytes:
    """Build the canonical JSON payload that was signed.

    The signing payload includes all token fields except ``signature``,
    serialized as canonical JSON (sorted keys, no whitespace).

    Args:
        token: The capability token to build the payload for.

    Returns:
        UTF-8 encoded canonical JSON bytes.
    """
    payload = {
        "token_id": str(token.token_id),
        "subject_node_id": token.subject_node_id,
        "issuer_domain": token.issuer_domain,
        "capabilities": sorted(token.capabilities),
        "issued_at": token.issued_at.isoformat(),
        "expires_at": token.expires_at.isoformat(),
        "issuer_public_key": token.issuer_public_key,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return canonical.encode("utf-8")


class ServiceCapabilityTokenVerifier:
    """Verifies capability tokens using Ed25519 signatures and trust roots.

    Stateless after construction. Thread safety depends on the underlying
    key provider implementation.

    Args:
        key_provider: Provider for domain trust root and node identity keys.

    .. versionadded:: 0.21.0
    """

    def __init__(self, key_provider: ProtocolMultiKeyProvider) -> None:
        self._key_provider = key_provider

    def verify_token(
        self,
        token: ModelCapabilityToken,
        required_capability: str,
    ) -> ModelResolutionProof:
        """Verify a capability token for a specific capability.

        Checks expiration, trust root, signature, and capability match.
        Returns a proof recording the verification outcome.

        Args:
            token: The capability token to verify.
            required_capability: The capability that must be attested
                by the token.

        Returns:
            A ``ModelResolutionProof`` with ``verified=True`` on success,
            or ``verified=False`` with descriptive notes on failure.
        """
        now = datetime.now(UTC)

        # Step 1: Check expiration
        if now >= token.expires_at:
            return self._failure_proof(
                token=token,
                notes=f"Token expired at {token.expires_at.isoformat()}",
                verified_at=now,
            )

        # Also check issued_at is not in the future (clock skew protection)
        if token.issued_at > now:
            return self._failure_proof(
                token=token,
                notes=f"Token issued_at {token.issued_at.isoformat()} is in the future",
                verified_at=now,
            )

        # Step 2: Retrieve issuer trust root
        trust_root_bytes = self._key_provider.get_domain_trust_root(token.issuer_domain)
        if trust_root_bytes is None:
            return self._failure_proof(
                token=token,
                notes=(
                    f"No trust root found for issuer domain '{token.issuer_domain}'"
                ),
                verified_at=now,
            )

        # Step 3: Decode the issuer public key from the token
        try:
            token_issuer_key_bytes = base64.urlsafe_b64decode(token.issuer_public_key)
        except (ValueError, TypeError):
            return self._failure_proof(
                token=token,
                notes="Invalid base64 encoding for issuer_public_key",
                verified_at=now,
            )

        # Step 4: Verify issuer key matches trust root
        if token_issuer_key_bytes != trust_root_bytes:
            return self._failure_proof(
                token=token,
                notes=(
                    f"Token issuer key does not match trust root for "
                    f"domain '{token.issuer_domain}'"
                ),
                verified_at=now,
            )

        # Step 5: Verify Ed25519 signature
        signing_payload = _build_signing_payload(token)
        if not verify_base64(trust_root_bytes, signing_payload, token.signature):
            return self._failure_proof(
                token=token,
                notes="Ed25519 signature verification failed",
                verified_at=now,
            )

        # Step 6: Confirm capability match
        if required_capability not in token.capabilities:
            return self._failure_proof(
                token=token,
                notes=(
                    f"Token does not attest capability '{required_capability}'; "
                    f"attested: {token.capabilities}"
                ),
                verified_at=now,
            )

        # All checks passed
        return ModelResolutionProof(
            proof_type=EnumProofType.CAPABILITY_ATTESTED,
            verified=True,
            verification_notes=(
                f"Token {token.token_id} verified for capability "
                f"'{required_capability}' issued by '{token.issuer_domain}'"
            ),
            token=token,
            verified_at=now,
        )

    def _failure_proof(
        self,
        token: ModelCapabilityToken,
        notes: str,
        verified_at: datetime,
    ) -> ModelResolutionProof:
        """Build a failed verification proof.

        Args:
            token: The token that failed verification.
            notes: Failure reason description.
            verified_at: When verification was attempted.

        Returns:
            A ``ModelResolutionProof`` with ``verified=False``.
        """
        logger.debug(
            "Token %s verification failed: %s",
            token.token_id,
            notes,
        )
        return ModelResolutionProof(
            proof_type=EnumProofType.CAPABILITY_ATTESTED,
            verified=False,
            verification_notes=notes,
            token=token,
            verified_at=verified_at,
        )

    def __repr__(self) -> str:
        """Return representation for debugging."""
        return f"ServiceCapabilityTokenVerifier(key_provider={self._key_provider!r})"

    def __str__(self) -> str:
        """Return string representation."""
        return "ServiceCapabilityTokenVerifier"
