# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Protocol for runtime public key lookup.

The key provider abstraction enables:
- Pluggable key storage backends (file, database, Vault)
- Testable signature verification (mock providers)
- Key rotation without code changes
- Fail-closed security (no key = no trust)

Design Principle:
    Signature verification MUST fail if the runtime_id's public key
    is not found. This is a security boundary - unknown runtimes
    are not trusted, period.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolKeyProvider(Protocol):
    """
    Protocol for looking up runtime public keys.

    Implementations provide storage and retrieval of Ed25519 public keys
    keyed by runtime_id. The runtime_id is the gateway/runtime that
    signed an envelope - NOT the emitter_identity.

    Security Model:
        - Signatures are bound to runtime_id (the gateway)
        - emitter_identity is for observability, not authentication
        - Unknown runtime_id = untrusted envelope = rejection

    Example:
        >>> provider = FileKeyProvider("/etc/onex/keys.json")
        >>> public_key = provider.get_public_key("runtime-dev-001")
        >>> if public_key is None:
        ...     raise SecurityError("Unknown runtime")
    """

    def get_public_key(self, runtime_id: str) -> bytes | None:
        """
        Retrieve the public key for a runtime.

        Args:
            runtime_id: The runtime identifier (gateway that signed).

        Returns:
            32-byte Ed25519 public key, or None if not found.

        Note:
            Callers MUST treat None as "untrusted" and reject
            the envelope. This is a security boundary.
        """
        ...

    def register_key(self, runtime_id: str, public_key: bytes) -> None:
        """
        Register a public key for a runtime.

        Args:
            runtime_id: The runtime identifier.
            public_key: 32-byte Ed25519 public key.

        Raises:
            ValueError: If public_key is not 32 bytes.

        Note:
            In production, key registration should be controlled
            through secure administrative channels, not runtime APIs.
        """
        ...

    def has_key(self, runtime_id: str) -> bool:
        """
        Check if a runtime's public key is registered.

        Args:
            runtime_id: The runtime identifier.

        Returns:
            True if the key is registered, False otherwise.
        """
        ...

    def list_runtime_ids(self) -> list[str]:
        """
        List all registered runtime IDs.

        Returns:
            List of runtime identifiers with registered keys.
        """
        ...


__all__ = ["ProtocolKeyProvider"]
