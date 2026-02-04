"""
File-backed implementation of ProtocolKeyProvider.

This implementation stores runtime public keys in a JSON file,
suitable for development, testing, and simple deployments.

File Format:
    {
        "keys": {
            "runtime-dev-001": "base64-encoded-public-key",
            "runtime-prod-001": "base64-encoded-public-key"
        }
    }

For production deployments, consider PostgresKeyProvider or
VaultKeyProvider instead.
"""

from __future__ import annotations

import base64
import json
import os
import threading
from pathlib import Path


class FileKeyProvider:
    """
    File-backed key provider for runtime public keys.

    Thread-safe implementation that caches keys in memory and
    persists changes to disk. Supports hot-reload of the key file.

    Attributes:
        key_file: Path to the JSON key file.

    Example:
        >>> provider = FileKeyProvider("/etc/onex/runtime_keys.json")
        >>> provider.register_key("runtime-dev-001", public_key_bytes)
        >>> key = provider.get_public_key("runtime-dev-001")
    """

    ED25519_PUBLIC_KEY_LENGTH = 32

    def __init__(self, key_file: str | Path) -> None:
        """
        Initialize the file key provider.

        Args:
            key_file: Path to the JSON key file. Created if it doesn't exist.
        """
        self._key_file = Path(key_file)
        self._keys: dict[str, bytes] = {}
        self._lock = threading.RLock()
        self._load_keys()

    def _load_keys(self) -> None:
        """Load keys from the file if it exists."""
        with self._lock:
            if not self._key_file.exists():
                self._keys = {}
                return

            try:
                data = json.loads(self._key_file.read_text(encoding="utf-8"))
                keys_data: dict[str, str] = data.get("keys", {})
                # Validate and load only keys with correct length
                loaded_keys: dict[str, bytes] = {}
                for runtime_id, key_b64 in keys_data.items():
                    key_bytes = base64.urlsafe_b64decode(key_b64)
                    if len(key_bytes) == self.ED25519_PUBLIC_KEY_LENGTH:
                        loaded_keys[runtime_id] = key_bytes
                    # Skip invalid-length keys silently (corrupt data)
                self._keys = loaded_keys
            except (json.JSONDecodeError, KeyError, ValueError):
                # Invalid file format - start fresh
                self._keys = {}

    def _save_keys(self) -> None:
        """Save keys to the file."""
        with self._lock:
            keys_data = {
                runtime_id: base64.urlsafe_b64encode(key).decode("ascii")
                for runtime_id, key in self._keys.items()
            }
            data: dict[str, dict[str, str]] = {"keys": keys_data}

            # Set restrictive umask BEFORE any filesystem operations to prevent TOCTOU
            # race condition where directories/files could be read by others during
            # the window between creation and permission setting
            old_umask = os.umask(0o077)  # Restrict to owner-only (rwx------)
            try:
                # Create parent directory with restrictive permissions
                self._key_file.parent.mkdir(parents=True, exist_ok=True)
                # Write file with restrictive permissions
                self._key_file.write_text(
                    json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
                )
            finally:
                os.umask(old_umask)  # Restore original umask

    def get_public_key(
        self,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
    ) -> bytes | None:
        """
        Retrieve the public key for a runtime.

        Args:
            runtime_id: The runtime identifier.

        Returns:
            32-byte Ed25519 public key, or None if not found.
        """
        with self._lock:
            return self._keys.get(runtime_id)

    def register_key(
        self,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
        public_key: bytes,
    ) -> None:
        """
        Register a public key for a runtime.

        Args:
            runtime_id: The runtime identifier.
            public_key: 32-byte Ed25519 public key.

        Raises:
            ValueError: If public_key is not 32 bytes.
        """
        if len(public_key) != self.ED25519_PUBLIC_KEY_LENGTH:
            msg = f"Public key must be {self.ED25519_PUBLIC_KEY_LENGTH} bytes, got {len(public_key)}"
            raise ValueError(msg)  # error-ok: Standard validation at function boundary

        with self._lock:
            self._keys[runtime_id] = public_key
            self._save_keys()

    def has_key(
        self,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
    ) -> bool:
        """Check if a runtime's public key is registered."""
        with self._lock:
            return runtime_id in self._keys

    def list_runtime_ids(self) -> list[str]:
        """List all registered runtime IDs."""
        with self._lock:
            return list(self._keys.keys())

    def remove_key(
        self,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
    ) -> bool:
        """
        Remove a runtime's public key.

        Args:
            runtime_id: The runtime identifier.

        Returns:
            True if key was removed, False if it didn't exist.
        """
        with self._lock:
            if runtime_id in self._keys:
                del self._keys[runtime_id]
                self._save_keys()
                return True
            return False

    def reload(self) -> None:
        """Reload keys from the file (hot-reload support)."""
        self._load_keys()


__all__ = ["FileKeyProvider"]
