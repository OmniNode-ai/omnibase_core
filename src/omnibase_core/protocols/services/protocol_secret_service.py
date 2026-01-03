"""
Secret service protocol for secure credential retrieval.

This module provides the protocol definition for secret/credential services
used in effect execution for template resolution.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSecretService(Protocol):
    """
    Protocol for secret retrieval services.

    Implementations should provide secure access to secrets/credentials
    for use in effect template resolution (e.g., API keys, passwords).

    This protocol is used by MixinEffectExecution for resolving
    secret placeholders in effect templates (e.g., "${secret.api_key}").

    Example implementation:
        class VaultSecretService:
            def __init__(self, vault_client: VaultClient) -> None:
                self._vault_client = vault_client

            def get_secret(self, key: str) -> str | None:
                return self._vault_client.read(key)

        class EnvSecretService:
            def get_secret(self, key: str) -> str | None:
                import os
                return os.environ.get(key)
    """

    def get_secret(self, key: str) -> str | None:
        """
        Retrieve a secret value by key.

        Args:
            key: The secret identifier/path. This is the portion after
                "secret." in template placeholders (e.g., for
                "${secret.api_key}", key would be "api_key").

        Returns:
            The secret value if found, None otherwise.
            Returning None indicates the secret was not found,
            which will raise a ModelOnexError in effect execution.
        """
        ...


__all__ = ["ProtocolSecretService"]
