# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceApprovalTokenValidator — HITL approval token validation for the risk gate.

## Token Format

Approval tokens are signed JWTs (HS256 or RS256) or opaque HMAC-SHA256 tokens
with the following payload structure:

    {
        "jti": "<uuid>",           // unique token ID (for replay detection)
        "sub": "<principal>",      // principal who approved
        "scope": "<command_ref>",  // command this approval covers
        "iat": <unix_timestamp>,   // issued at
        "exp": <unix_timestamp>,   // expiry (max 24h from issuance)
    }

## Phase 1 Behavior

This implementation performs structural validation only:

- Token must be non-empty and parse as a ``<header>.<payload>.<sig>`` JWT.
- Token scope must match the requested ``command_ref``.
- Token expiry must be in the future (requires ``exp`` field).
- ``jti`` must be present (replay rejection is enforced by the caller with
  ``ServiceRiskGate`` tracking used JTIs in memory).
- Principal must be non-empty.

## Phase 2 Integration

Replace ``ServiceApprovalTokenValidator`` with a real implementation that:

1. Fetches the approval service public key (or HMAC secret) from Infisical.
2. Verifies the JWT signature (RS256 or HS256 depending on deployment mode).
3. Checks the token against the approval service revocation list.
4. Returns a validated ``ModelApprovalTokenValidationResult`` with the real
   ``principal`` extracted from the verified JWT.

## Token Replay Prevention

Phase 1: ``ServiceRiskGate`` tracks used ``jti`` values in memory for the
lifetime of the process. Tokens with repeated ``jti`` are rejected.

Phase 2: the approval service should mark tokens as consumed on first use.
The validator returns the ``token_jti`` so the caller can track replay state.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

import base64
import json
import time
import uuid

from omnibase_core.models.cli.model_approval_token_validation_result import (
    ModelApprovalTokenValidationResult,
)

__all__ = ["ServiceApprovalTokenValidator"]


class ServiceApprovalTokenValidator:
    """Validate HITL approval tokens for the registry-driven CLI risk gate.

    ## Phase 1

    Performs structural and scope validation without cryptographic verification.
    Tokens are expected to be base64url-encoded JWT payloads or opaque strings
    with the structure ``<header_b64>.<payload_b64>.<sig_b64>``.

    If the token does not parse as a JWT, it is rejected with a clear message.

    ## Phase 2

    Subclass or replace with a real implementation that calls the approval
    service endpoint and verifies the JWT signature. The ``validate()`` interface
    is stable — swap implementations without changing callers.

    Example (Phase 1 usage)::

        validator = ServiceApprovalTokenValidator()
        result = validator.validate(token="<jwt>", command_ref="com.omninode.memory.purge")
        if not result.valid:
            print(f"Token rejected: {result.rejection_reason}")

    .. versionadded:: 0.20.0  (OMN-2562)
    """

    def validate(
        self,
        token: str,
        command_ref: str,
    ) -> ModelApprovalTokenValidationResult:
        """Validate an approval token against the given command reference.

        Checks:
        1. Token is non-empty and parseable as JWT.
        2. ``scope`` field matches ``command_ref`` exactly.
        3. ``exp`` field is present and in the future.
        4. ``jti`` field is present (replay detection key).
        5. ``sub`` (principal) field is non-empty.

        Args:
            token: The approval token string (JWT or opaque token).
            command_ref: The namespaced command reference this token must be scoped to.

        Returns:
            ``ModelApprovalTokenValidationResult`` with ``valid=True`` on
            success, or ``valid=False`` with a ``rejection_reason`` on failure.
        """
        if not token or not token.strip():
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token is empty.",
            )

        # Parse JWT payload (structural validation only in Phase 1)
        payload = self._parse_jwt_payload(token)
        if payload is None:
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason=(
                    "Token is not a valid JWT. Expected format: "
                    "<header_b64>.<payload_b64>.<sig_b64>."
                ),
            )

        # Validate scope matches command_ref
        scope = payload.get("scope", "")
        if scope != command_ref:
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason=(
                    f"Token scope '{scope}' does not match command '{command_ref}'. "
                    "This token was issued for a different command."
                ),
            )

        # Validate expiry
        exp = payload.get("exp")
        if exp is None:
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token missing 'exp' (expiry) field.",
            )
        if not isinstance(exp, (int, float)):
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token 'exp' field is not a valid timestamp.",
            )
        if time.time() > float(exp):
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token has expired.",
            )

        # Validate jti (required for replay detection)
        jti = payload.get("jti", "")
        if not jti or not isinstance(jti, str):
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token missing 'jti' (unique token ID) field.",
            )

        # Validate principal (sub)
        principal = payload.get("sub", "")
        if not principal or not isinstance(principal, str):
            return ModelApprovalTokenValidationResult(
                valid=False,
                command_ref=command_ref,
                rejection_reason="Token missing 'sub' (principal) field.",
            )

        return ModelApprovalTokenValidationResult(
            valid=True,
            command_ref=command_ref,
            principal=principal,
            token_jti=jti,
        )

    @staticmethod
    def _parse_jwt_payload(token: str) -> dict[str, object] | None:
        """Parse the JWT payload section from a token string.

        Accepts standard ``<header>.<payload>.<sig>`` JWT format.
        Returns the decoded payload dict, or ``None`` if parsing fails.

        Args:
            token: Raw token string.

        Returns:
            Decoded payload dict, or ``None`` on parse failure.
        """
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None

        # Decode the payload (middle section)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            if not isinstance(payload, dict):
                return None
            return payload
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def create_stub_token(  # stub-ok
        command_ref: str,
        principal: str = "stub-principal",
        ttl_seconds: int = 3600,
    ) -> str:
        """Create an unsigned approval token for testing and local development.

        Produces a valid-structure JWT with an unsigned payload. This method
        generates a complete, parseable token with all required fields populated.
        Not for production use — this token has no cryptographic signature.

        Args:
            command_ref: The command reference to scope this token to.
            principal: The principal to embed in the token.
            ttl_seconds: Token lifetime in seconds (default: 1 hour).

        Returns:
            An unsigned JWT string (for testing and local development only).
        """
        header = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"alg": "none", "typ": "JWT"}, separators=(",", ":")
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )

        payload_data = {
            "jti": str(uuid.uuid4()),
            "sub": principal,
            "scope": command_ref,
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl_seconds,
        }
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(payload_data, separators=(",", ":")).encode()
            )
            .rstrip(b"=")
            .decode()
        )

        return f"{header}.{payload}.stub-sig"
