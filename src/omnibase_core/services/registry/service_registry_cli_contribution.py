# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceRegistryCliContribution — Registry for cli.contribution.v1 contracts.

This module provides the ServiceRegistryCliContribution class for storing,
retrieving, and validating CLI contribution contracts published by nodes in
the ONEX registry-driven CLI system.

Responsibilities:
    - Accept and validate cli.contribution.v1 contracts from publishing nodes.
    - Enforce global command ID uniqueness across all publishers.
    - Reject malformed contracts (bad fingerprint, failed signature verification).
    - Serve contracts and command entries for catalog materialization.

Thread Safety:
    All operations are protected by threading.RLock for reentrant safety.

Scale:
    Designed for deployments with fewer than 10,000 registered commands.
    For larger deployments, consider sharding by publisher namespace.

Related:
    - ModelCliContribution: The contract model stored in this registry.
    - OMN-2536: Foundational contract definition for the registry-driven CLI.

.. versionadded:: 1.0.0
"""

from __future__ import annotations

__all__ = ["ServiceRegistryCliContribution"]

import threading
from typing import TYPE_CHECKING

from omnibase_core.crypto.crypto_ed25519_signer import verify_base64
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_command_entry import (
        ModelCliCommandEntry,
    )
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliContribution,
    )


class ServiceRegistryCliContribution:
    """In-memory thread-safe registry for cli.contribution.v1 contracts.

    Stores contracts keyed by publisher node ID. Enforces:
    1. Contract fingerprint integrity (validated during registration via Pydantic).
    2. Signature verification using the embedded signer_public_key.
    3. Global command ID uniqueness across all publishers.

    Attributes:
        _contracts: Dict mapping publisher ID to ModelCliContribution.
        _command_index: Dict mapping command ID to publisher ID for collision detection.
        _lock: RLock for thread-safe access.

    Example:
        .. code-block:: python

            from omnibase_core.services.registry.service_registry_cli_contribution import (
                ServiceRegistryCliContribution,
            )

            registry = ServiceRegistryCliContribution()
            registry.publish(contribution)

            # Look up all commands from a publisher
            contract = registry.get(publisher_id="com.omninode.memory")
            assert contract is not None

            # Find command by ID
            entry = registry.get_command("com.omninode.memory.query")
            assert entry is not None

    .. versionadded:: 1.0.0
    """

    def __init__(self) -> None:
        """Initialize an empty ServiceRegistryCliContribution."""
        self._contracts: dict[str, ModelCliContribution] = {}
        self._command_index: dict[str, str] = {}  # command_id -> publisher_id
        self._lock = threading.RLock()

    def publish(
        self,
        contribution: ModelCliContribution,
        replace: bool = False,
        verify_signature: bool = True,
    ) -> None:
        """Publish a cli.contribution.v1 contract to the registry.

        Validates the contract (fingerprint already checked by Pydantic model),
        optionally verifies the Ed25519 signature, and checks global command ID
        uniqueness before storing.

        Args:
            contribution: A valid ModelCliContribution instance.
            replace: If True, replace existing contract for this publisher.
                If False (default), raise ModelOnexError on duplicate publisher.
            verify_signature: If True (default), verify the Ed25519 signature.
                Set False only in tests or when signature checking is handled
                at a higher layer.

        Raises:
            ModelOnexError: If:
                - Publisher already registered and replace=False.
                - Signature verification fails.
                - A command ID collides with a different publisher's command.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        publisher = contribution.publisher

        if verify_signature:
            self._verify_contribution_signature(contribution)

        with self._lock:
            # Check for duplicate publisher
            if publisher in self._contracts and not replace:
                raise ModelOnexError(
                    message=(
                        f"Publisher '{publisher}' already has a registered contribution. "
                        "Use replace=True to update."
                    ),
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                    publisher=publisher,
                )

            # Check for command ID collisions across publishers
            for cmd in contribution.commands:
                existing_publisher = self._command_index.get(cmd.id)
                if existing_publisher is not None and existing_publisher != publisher:
                    raise ModelOnexError(
                        message=(
                            f"Command ID collision: '{cmd.id}' is already registered "
                            f"by publisher '{existing_publisher}'. "
                            "Command IDs must be globally unique."
                        ),
                        error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                        command_id=cmd.id,
                        existing_publisher=existing_publisher,
                        new_publisher=publisher,
                    )

            # If replacing, remove old command index entries for this publisher
            if replace and publisher in self._contracts:
                old_contract = self._contracts[publisher]
                for cmd in old_contract.commands:
                    self._command_index.pop(cmd.id, None)

            # Store contract and update command index
            self._contracts[publisher] = contribution
            for cmd in contribution.commands:
                self._command_index[cmd.id] = publisher

    def get(self, publisher_id: str) -> ModelCliContribution | None:
        """Get the contribution contract for a specific publisher.

        Args:
            publisher_id: The publisher node ID to look up.

        Returns:
            The ModelCliContribution if found, None otherwise.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return self._contracts.get(publisher_id)

    def get_command(self, command_id: str) -> ModelCliCommandEntry | None:
        """Find a command entry by its globally namespaced ID.

        Args:
            command_id: The fully qualified command ID to find.

        Returns:
            The ModelCliCommandEntry if found, None otherwise.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            publisher_id = self._command_index.get(command_id)
            if publisher_id is None:
                return None
            contract = self._contracts.get(publisher_id)
            if contract is None:
                return None
            for cmd in contract.commands:
                if cmd.id == command_id:
                    return cmd
            return None

    def unpublish(self, publisher_id: str) -> bool:
        """Remove a publisher's contribution contract from the registry.

        Args:
            publisher_id: The publisher node ID to remove.

        Returns:
            True if the contract was found and removed, False if not found.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            contract = self._contracts.pop(publisher_id, None)
            if contract is None:
                return False
            for cmd in contract.commands:
                self._command_index.pop(cmd.id, None)
            return True

    def list_all(self) -> list[ModelCliContribution]:
        """List all registered contribution contracts.

        Returns:
            List of ModelCliContribution instances in insertion order.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return list(self._contracts.values())

    def list_all_commands(self) -> list[ModelCliCommandEntry]:
        """List all registered command entries across all publishers.

        Returns:
            Flat list of all ModelCliCommandEntry objects.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            result: list[ModelCliCommandEntry] = []
            for contract in self._contracts.values():
                result.extend(contract.commands)
            return result

    def list_publishers(self) -> list[str]:
        """List all registered publisher IDs.

        Returns:
            List of publisher IDs in insertion order.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return list(self._contracts.keys())

    def has_command(self, command_id: str) -> bool:
        """Check if a command ID is registered.

        Args:
            command_id: The command ID to check.

        Returns:
            True if registered, False otherwise.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return command_id in self._command_index

    def clear(self) -> None:
        """Remove all registered contracts.

        Thread Safety:
            This method is protected by the internal RLock.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            self._contracts.clear()
            self._command_index.clear()

    def __len__(self) -> int:
        """Return the number of registered publisher contracts.

        Returns:
            int: Count of registered publishers.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return len(self._contracts)

    def __contains__(self, publisher_id: str) -> bool:
        """Check if a publisher ID is registered.

        Args:
            publisher_id: The publisher node ID to check.

        Returns:
            bool: True if registered, False otherwise.

        .. versionadded:: 1.0.0
        """
        with self._lock:
            return publisher_id in self._contracts

    def __repr__(self) -> str:
        """Return a string representation for debugging.

        Returns:
            str: Format "ServiceRegistryCliContribution(publishers=N, commands=M)"
        """
        with self._lock:
            return (
                f"ServiceRegistryCliContribution("
                f"publishers={len(self._contracts)}, "
                f"commands={len(self._command_index)})"
            )

    @staticmethod
    def _verify_contribution_signature(
        contribution: ModelCliContribution,
    ) -> None:
        """Verify the Ed25519 signature on a contribution contract.

        Args:
            contribution: The contribution to verify.

        Raises:
            ModelOnexError: If signature verification fails.
        """
        import base64

        try:
            public_key_bytes = base64.urlsafe_b64decode(
                contribution.signer_public_key + "=="
            )
        except Exception as exc:
            raise ModelOnexError(
                message=(
                    f"Failed to decode signer_public_key for publisher "
                    f"'{contribution.publisher}': {exc}"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                publisher=contribution.publisher,
            ) from exc

        fingerprint_bytes = contribution.fingerprint.encode("utf-8")
        is_valid = verify_base64(
            public_key_bytes=public_key_bytes,
            data=fingerprint_bytes,
            signature_b64=contribution.signature,
        )
        if not is_valid:
            raise ModelOnexError(
                message=(
                    f"Signature verification failed for publisher '{contribution.publisher}'. "
                    "The contract may have been tampered with or signed with a different key."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                publisher=contribution.publisher,
                fingerprint=contribution.fingerprint[:12] + "...",
            )
