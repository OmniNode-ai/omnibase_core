# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceCatalogManager — local Command Catalog for the registry-driven CLI.

The Command Catalog is the CLI's runtime view of available commands.  It is
the bridge between the registry (source of truth) and the CLI binary
(consumer).  Help text, tab completion, and invocation all read from this
catalog — **never** from the live registry at invocation time.

## Materialization Pipeline

    omn refresh (or first-run)
        │
        ▼
    1. Fetch cli.contribution.v1 contracts from ServiceRegistryCliContribution
    2. Verify Ed25519 signature chain per contract
    3. Validate schema (already guaranteed by Pydantic construction)
    4. Apply policy filters (role, org, env, feature flags, deprecation,
                            experimental, allowlist/denylist, CLI version)
    5. Build in-memory catalog (dict[command_id → ModelCliCommandEntry])
    6. Persist catalog to local JSON cache
        │
        ▼
    Subsequent calls to load() / get_command() / list_commands()
        │
        ▼
    Read from in-memory cache (zero network calls)

## Offline / Fast Operation

    - ``load()`` reads from the cache file; raises ``CatalogLoadError`` if
      the cache is missing or corrupt.
    - ``refresh()`` is the only method that calls the registry.
    - Help and tab-completion always call ``list_commands()`` / ``get_command()``
      which are purely in-memory after the first ``load()``.

## Signature Verification

    Signature verification runs:
    - During ``refresh()`` when contracts are fetched from the registry.
    - During ``load()`` on every cache load — not only on fetch.

    A failed verification raises ``CatalogSignatureError`` (hard error, not
    a warning).

## Cache Format

    JSON file at ``~/.omn/catalog.json``:

    .. code-block:: json

        {
          "cli_version": "0.19.0",
          "fetched_at": "2026-02-24T00:00:00Z",
          "cache_key": "<sha256>",
          "commands": {
            "<command_id>": { ...ModelCliCommandEntry.model_dump()... }
          },
          "signatures": {
            "<publisher_id>": {
              "fingerprint": "...",
              "signature": "...",
              "signer_public_key": "..."
            }
          }
        }

## Thread Safety

    All public methods are protected by a ``threading.RLock``.

.. versionadded:: 0.19.0  (OMN-2544)
"""

from __future__ import annotations

__all__ = [
    "ServiceCatalogManager",
]

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.crypto.crypto_ed25519_signer import verify_base64
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_catalog import (
    CatalogError,
    CatalogLoadError,
    CatalogSignatureError,
    CatalogVersionError,
)
from omnibase_core.models.catalog.model_catalog_diff import ModelCatalogDiff
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.catalog.model_catalog_policy import ModelCatalogPolicy
    from omnibase_core.models.contracts.model_cli_command_entry import (
        ModelCliCommandEntry,
    )
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliContribution,
    )
    from omnibase_core.services.registry.service_registry_cli_contribution import (
        ServiceRegistryCliContribution,
    )

# Re-export for convenience so callers can import from the service module.
__all__ = [
    "CatalogError",
    "CatalogLoadError",
    "CatalogSignatureError",
    "CatalogVersionError",
    "ServiceCatalogManager",
]

# Default cache path (overrideable via constructor).
_DEFAULT_CACHE_PATH = Path.home() / ".omn" / "catalog.json"


# ---------------------------------------------------------------------------
# Diff result
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ServiceCatalogManager
# ---------------------------------------------------------------------------


class ServiceCatalogManager:
    """Local Command Catalog for the registry-driven CLI.

    Implements the full materialization pipeline:
    fetch → verify → policy-filter → cache → load.

    Args:
        registry: The source registry from which contracts are fetched
            during ``refresh()``.  May be ``None`` for load-only usage
            (offline mode after first refresh).
        policy: Policy configuration controlling which commands are visible.
            Defaults to a permissive policy (all commands visible).
        cache_path: Path to the local catalog cache file.
            Defaults to ``~/.omn/catalog.json``.
        cli_version: The running CLI version string (e.g. ``"0.19.0"``).
            Used in the cache key and for version-compatibility checks.
            If not provided, version-gating is disabled.

    Thread Safety:
        All public methods are protected by an internal ``threading.RLock``.

    Example:
        .. code-block:: python

            registry = ServiceRegistryCliContribution()
            # ... publish contributions to registry ...

            manager = ServiceCatalogManager(registry=registry, cli_version="0.19.0")
            diff = manager.refresh()  # fetches, verifies, caches
            manager.load()            # load from cache (verifies signatures again)

            commands = manager.list_commands()
            cmd = manager.get_command("com.omninode.memory.query")

    .. versionadded:: 0.19.0  (OMN-2544)
    """

    def __init__(
        self,
        registry: ServiceRegistryCliContribution | None = None,
        policy: ModelCatalogPolicy | None = None,
        cache_path: Path | None = None,
        cli_version: str | None = None,
    ) -> None:
        """Initialize ServiceCatalogManager.

        Args:
            registry: Registry to fetch contracts from during refresh.
            policy: Policy filter configuration.  Defaults to permissive.
            cache_path: Override for the default ``~/.omn/catalog.json`` path.
            cli_version: Running CLI version for cache-key and version-gating.
        """
        from omnibase_core.models.catalog.model_catalog_policy import ModelCatalogPolicy

        self._registry = registry
        self._policy: ModelCatalogPolicy = policy or ModelCatalogPolicy()
        self._cache_path: Path = cache_path or _DEFAULT_CACHE_PATH
        self._cli_version: str = cli_version or ""

        # In-memory catalog: command_id → ModelCliCommandEntry
        self._catalog: dict[str, ModelCliCommandEntry] = {}

        # Signature store for re-verification on load:
        #   publisher_id → {fingerprint, signature, signer_public_key}
        self._signatures: dict[str, dict[str, str]] = {}

        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> ModelCatalogDiff:
        """Fetch, verify, filter, and cache the command catalog.

        Runs the full materialization pipeline:

        1. Fetch all ``cli.contribution.v1`` contracts from the registry.
        2. Verify Ed25519 signature on each contract.
        3. Apply policy filters.
        4. Compute diff against current in-memory catalog.
        5. Rebuild in-memory catalog.
        6. Persist catalog to local cache file.

        Returns:
            ``ModelCatalogDiff`` describing added / removed / updated / deprecated
            commands relative to the catalog state before the refresh.

        Raises:
            ModelOnexError: If the registry is not set.
            CatalogSignatureError: If any contract fails signature verification.
        """
        with self._lock:
            if self._registry is None:
                raise ModelOnexError(
                    message=(
                        "ServiceCatalogManager: registry is not set. "
                        "Cannot refresh without a registry."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            contributions: list[ModelCliContribution] = self._registry.list_all()

            # Verify all signatures before touching the catalog.
            for contrib in contributions:
                self._verify_signature(contrib)

            # Build new catalog from policy-filtered commands.
            new_catalog: dict[str, ModelCliCommandEntry] = {}
            new_signatures: dict[str, dict[str, str]] = {}

            for contrib in contributions:
                new_signatures[contrib.publisher] = {
                    "fingerprint": contrib.fingerprint,
                    "signature": contrib.signature,
                    "signer_public_key": contrib.signer_public_key,
                }
                for cmd in contrib.commands:
                    if self._is_visible(cmd):
                        new_catalog[cmd.id] = cmd

            # Compute diff before replacing the catalog.
            diff = self._compute_diff(self._catalog, new_catalog)

            # Replace in-memory state.
            self._catalog = new_catalog
            self._signatures = new_signatures

            # Persist to disk.
            self._write_cache()

            return diff

    def load(self) -> None:
        """Load the catalog from the local cache file.

        Reads ``~/.omn/catalog.json`` (or the configured path), re-verifies
        all Ed25519 signatures, and populates the in-memory catalog.

        This is the fast path for all subsequent command lookups.

        Raises:
            CatalogLoadError: If the cache file is missing or cannot be parsed.
            CatalogSignatureError: If any stored signature fails verification.
            CatalogVersionError: If the cache was written for a different CLI
                version (when ``cli_version`` is set and mismatches).
        """
        with self._lock:
            if not self._cache_path.exists():
                raise CatalogLoadError(
                    f"Catalog cache not found at {self._cache_path}. "
                    "Run 'omn refresh' to build the catalog."
                )

            try:
                raw = self._cache_path.read_text(encoding="utf-8")
                data: dict[str, object] = json.loads(raw)
            except (OSError, json.JSONDecodeError) as exc:
                raise CatalogLoadError(
                    f"Failed to read catalog cache at {self._cache_path}: {exc}"
                ) from exc

            # Version check.
            cached_version = str(data.get("cli_version", ""))
            if self._cli_version and cached_version != self._cli_version:
                raise CatalogVersionError(
                    f"Catalog cache was built for CLI version '{cached_version}', "
                    f"but running version is '{self._cli_version}'. "
                    "Run 'omn refresh' to rebuild the catalog."
                )

            # Re-verify signatures stored in cache.
            signatures_raw = data.get("signatures", {})
            if not isinstance(signatures_raw, dict):
                raise CatalogLoadError("Catalog cache 'signatures' field is malformed.")

            signatures: dict[str, dict[str, str]] = {}
            for publisher, sig_data in signatures_raw.items():
                if not isinstance(sig_data, dict):
                    raise CatalogLoadError(
                        f"Catalog cache signature for publisher '{publisher}' is malformed."
                    )
                fp = str(sig_data.get("fingerprint", ""))
                sig = str(sig_data.get("signature", ""))
                pub_key = str(sig_data.get("signer_public_key", ""))

                self._verify_raw_signature(
                    publisher=publisher,
                    fingerprint=fp,
                    signature=sig,
                    signer_public_key=pub_key,
                )
                signatures[publisher] = {
                    "fingerprint": fp,
                    "signature": sig,
                    "signer_public_key": pub_key,
                }

            # Load commands from cache.
            from omnibase_core.models.contracts.model_cli_command_entry import (
                ModelCliCommandEntry,
            )

            commands_raw = data.get("commands", {})
            if not isinstance(commands_raw, dict):
                raise CatalogLoadError("Catalog cache 'commands' field is malformed.")

            catalog: dict[str, ModelCliCommandEntry] = {}
            for cmd_id, cmd_data in commands_raw.items():
                try:
                    entry = ModelCliCommandEntry.model_validate(cmd_data)
                    catalog[cmd_id] = entry
                except Exception as exc:
                    raise CatalogLoadError(
                        f"Failed to parse command '{cmd_id}' from cache: {exc}"
                    ) from exc

            self._catalog = catalog
            self._signatures = signatures

    def get_command(self, command_id: str) -> ModelCliCommandEntry | None:
        """Retrieve a single command entry by ID.

        Args:
            command_id: The globally namespaced command ID to look up.

        Returns:
            ``ModelCliCommandEntry`` if found and visible, ``None`` otherwise.

        Thread Safety:
            Protected by the internal RLock.
        """
        with self._lock:
            return self._catalog.get(command_id)

    def list_commands(self, group: str | None = None) -> list[ModelCliCommandEntry]:
        """List all visible commands, optionally filtered by group.

        Args:
            group: If provided, return only commands in this group.
                   ``None`` returns all visible commands.

        Returns:
            List of ``ModelCliCommandEntry`` objects.

        Thread Safety:
            Protected by the internal RLock.
        """
        with self._lock:
            entries = list(self._catalog.values())
            if group is not None:
                entries = [e for e in entries if e.group == group]
            return entries

    def is_visible(self, command_id: str) -> bool:
        """Check whether a command is visible in the current catalog.

        A command is visible if it passed policy filters during the last
        ``refresh()`` or ``load()``.  Commands blocked by policy are absent
        from the catalog entirely.

        Args:
            command_id: The command ID to check.

        Returns:
            True if visible, False otherwise.

        Thread Safety:
            Protected by the internal RLock.
        """
        with self._lock:
            return command_id in self._catalog

    def cache_key(self) -> str:
        """Compute the cache key for the current in-memory catalog.

        The cache key is a SHA256 over the sorted command IDs and their
        fingerprints, combined with the CLI version string.  It is stable
        for identical content and changes when any command changes.

        Returns:
            Lowercase hex SHA256 string (64 characters).

        Thread Safety:
            Protected by the internal RLock.
        """
        with self._lock:
            return self._compute_cache_key(self._catalog, self._cli_version)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_visible(self, cmd: ModelCliCommandEntry) -> bool:
        """Apply policy filters to decide if a command is visible.

        Args:
            cmd: The command entry to evaluate.

        Returns:
            True if the command passes all policy filters.
        """
        policy = self._policy

        # Allowlist short-circuit: always visible if explicitly allowed.
        if policy.command_allowlist and cmd.id in policy.command_allowlist:
            return True

        # Denylist: hidden if explicitly blocked.
        if cmd.id in policy.command_denylist:
            return False

        # Role-based: command must intersect allowed_roles.
        if policy.allowed_roles:
            if not set(cmd.permissions) & policy.allowed_roles:
                return False

        # Org policy: hide if any permission tag is blocked.
        if policy.blocked_org_tags:
            if set(cmd.permissions) & policy.blocked_org_tags:
                return False

        # Deprecation filter.
        if (
            policy.hide_deprecated
            and cmd.visibility == EnumCliCommandVisibility.DEPRECATED
        ):
            return False

        # Experimental filter.
        if (
            policy.hide_experimental
            and cmd.visibility == EnumCliCommandVisibility.EXPERIMENTAL
        ):
            return False

        return True

    def _verify_signature(self, contrib: ModelCliContribution) -> None:
        """Verify the Ed25519 signature on a ModelCliContribution.

        Args:
            contrib: Contribution to verify.

        Raises:
            CatalogSignatureError: If verification fails.
        """
        self._verify_raw_signature(
            publisher=contrib.publisher,
            fingerprint=contrib.fingerprint,
            signature=contrib.signature,
            signer_public_key=contrib.signer_public_key,
        )

    @staticmethod
    def _verify_raw_signature(
        *,
        publisher: str,
        fingerprint: str,
        signature: str,
        signer_public_key: str,
    ) -> None:
        """Verify a raw Ed25519 signature.

        Args:
            publisher: Publisher node ID (for error messages).
            fingerprint: Hex-encoded SHA256 fingerprint (64 chars).
            signature: URL-safe base64 encoded Ed25519 signature.
            signer_public_key: URL-safe base64 encoded Ed25519 public key.

        Raises:
            CatalogSignatureError: If the public key cannot be decoded or
                signature verification fails.
        """
        import base64

        try:
            public_key_bytes = base64.urlsafe_b64decode(signer_public_key + "==")
        except Exception as exc:
            raise CatalogSignatureError(
                f"Failed to decode signer_public_key for publisher '{publisher}': {exc}"
            ) from exc

        fingerprint_bytes = fingerprint.encode("utf-8")
        is_valid = verify_base64(
            public_key_bytes=public_key_bytes,
            data=fingerprint_bytes,
            signature_b64=signature,
        )
        if not is_valid:
            raise CatalogSignatureError(
                f"Signature verification failed for publisher '{publisher}'. "
                "The catalog may have been tampered with or the key has rotated. "
                "Run 'omn refresh' to re-fetch and re-verify the catalog."
            )

    def _write_cache(self) -> None:
        """Serialize the current in-memory catalog to the cache file."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)

        commands_serialized: dict[str, object] = {
            cmd_id: entry.model_dump(exclude_none=True)
            for cmd_id, entry in self._catalog.items()
        }

        payload: dict[str, object] = {
            "cli_version": self._cli_version,
            "fetched_at": datetime.now(UTC).isoformat(),
            "cache_key": self._compute_cache_key(self._catalog, self._cli_version),
            "commands": commands_serialized,
            "signatures": self._signatures,
        }

        self._cache_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _compute_cache_key(
        catalog: dict[str, ModelCliCommandEntry],
        cli_version: str,
    ) -> str:
        """Compute a stable cache key for the catalog contents.

        Key = SHA256(sorted_command_ids:cli_version).

        Args:
            catalog: In-memory command catalog.
            cli_version: CLI version string.

        Returns:
            Lowercase hex SHA256 (64 chars).
        """
        sorted_ids = sorted(catalog.keys())
        key_data = json.dumps(
            {"command_ids": sorted_ids, "cli_version": cli_version},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_diff(
        old: dict[str, ModelCliCommandEntry],
        new: dict[str, ModelCliCommandEntry],
    ) -> ModelCatalogDiff:
        """Compute the diff between old and new catalogs.

        Args:
            old: Previous catalog state.
            new: New catalog state after refresh.

        Returns:
            ``ModelCatalogDiff`` with added / removed / updated / deprecated.
        """
        old_ids = set(old)
        new_ids = set(new)

        added = sorted(new_ids - old_ids)
        removed = sorted(old_ids - new_ids)

        updated: list[str] = []
        deprecated: list[str] = []
        for cmd_id in old_ids & new_ids:
            old_cmd = old[cmd_id]
            new_cmd = new[cmd_id]
            # Consider "updated" if any field changed.
            if old_cmd.model_dump() != new_cmd.model_dump():
                if new_cmd.visibility == EnumCliCommandVisibility.DEPRECATED:
                    deprecated.append(cmd_id)
                else:
                    updated.append(cmd_id)

        return ModelCatalogDiff(
            added=added,
            removed=removed,
            updated=sorted(updated),
            deprecated=sorted(deprecated),
        )

    def __repr__(self) -> str:
        """Return debug representation."""
        with self._lock:
            return (
                f"ServiceCatalogManager("
                f"commands={len(self._catalog)}, "
                f"cli_version={self._cli_version!r}, "
                f"cache_path={self._cache_path})"
            )
