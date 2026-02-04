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
import logging
import os
import stat
import tempfile
import threading
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)


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

    # Maximum allowable file permission mode for key files (owner read/write only)
    _MAX_ALLOWED_MODE = 0o600

    def _load_keys(self) -> None:
        """Load keys from the file if it exists."""
        with self._lock:
            if not self._key_file.exists():
                self._keys = {}
                return

            # Validate file permissions before loading - defense-in-depth for key integrity
            # Even though these are public keys (confidentiality not a concern), integrity
            # matters - an attacker who can write to a world-writable key file can inject
            # malicious runtime IDs
            self._validate_file_permissions()

            try:
                data = json.loads(self._key_file.read_text(encoding="utf-8"))
                keys_data: dict[str, str] = data.get("keys", {})
                # Validate and load only keys with correct length
                loaded_keys: dict[str, bytes] = {}
                for runtime_id, key_b64 in keys_data.items():
                    try:
                        key_bytes = base64.urlsafe_b64decode(key_b64)
                        if len(key_bytes) == self.ED25519_PUBLIC_KEY_LENGTH:
                            loaded_keys[runtime_id] = key_bytes
                        else:
                            logger.warning(
                                "Skipping key for runtime '%s': invalid length %d "
                                "(expected %d bytes)",
                                runtime_id,
                                len(key_bytes),
                                self.ED25519_PUBLIC_KEY_LENGTH,
                            )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            "Skipping key for runtime '%s': base64 decode failed: %s",
                            runtime_id,
                            type(e).__name__,
                        )
                self._keys = loaded_keys
            except json.JSONDecodeError as e:
                logger.warning(
                    "Key file %s has invalid JSON format: %s. Starting with empty keys.",
                    self._key_file,
                    e.msg,
                )
                self._keys = {}
            except (KeyError, ValueError) as e:
                logger.warning(
                    "Key file %s has invalid structure: %s. Starting with empty keys.",
                    self._key_file,
                    type(e).__name__,
                )
                self._keys = {}

    def _validate_file_permissions(self) -> None:
        """
        Validate file permissions are restrictive enough.

        Checks that group and other users have no access (mode & 0o077 == 0).
        Raises ModelOnexError if permissions are insecure (fail-closed security).

        Raises:
            ModelOnexError: If file has insecure permissions (group/other access
                or special permission bits like setuid/setgid).
        """
        file_stat = self._key_file.stat()
        file_mode = file_stat.st_mode

        # Extract permission bits only (ignore file type bits)
        permission_bits = file_mode & 0o777

        # Check for group/other access (security concern) - FAIL CLOSED
        group_other_bits = permission_bits & 0o077
        if group_other_bits != 0:
            raise ModelOnexError(
                message=(
                    f"Key file {self._key_file} has insecure permissions {permission_bits:04o}: "
                    f"group/other access bits are set ({group_other_bits:04o}). "
                    f"This may allow unauthorized key modification. "
                    f"Fix with: chmod 600 {self._key_file}"
                ),
                error_code=EnumCoreErrorCode.PERMISSION_ERROR,
                file_path=str(self._key_file),
                permission_bits=f"{permission_bits:04o}",
                group_other_bits=f"{group_other_bits:04o}",
            )

        # Check for special bits (setuid, setgid, sticky) - unusual for key files
        special_bits = file_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX)
        if special_bits != 0:
            special_names = []
            if file_mode & stat.S_ISUID:
                special_names.append("setuid")
            if file_mode & stat.S_ISGID:
                special_names.append("setgid")
            if file_mode & stat.S_ISVTX:
                special_names.append("sticky")
            raise ModelOnexError(
                message=(
                    f"Key file {self._key_file} has unusual special permission bits: "
                    f"{', '.join(special_names)}. This is unexpected for a key file."
                ),
                error_code=EnumCoreErrorCode.PERMISSION_ERROR,
                file_path=str(self._key_file),
                special_bits=special_names,
            )

    def _save_keys(self) -> None:
        """
        Save keys to the file atomically.

        Uses atomic write pattern (temp file + rename) to prevent:
        - Partial file exposure to concurrent readers
        - Data corruption on crash during write

        Uses os.open() with explicit mode flags instead of umask to ensure:
        - Thread-safety (umask is process-wide, not thread-safe)
        - Correct permissions from creation (no TOCTOU window)
        """
        with self._lock:
            keys_data = {
                runtime_id: base64.urlsafe_b64encode(key).decode("ascii")
                for runtime_id, key in self._keys.items()
            }
            data: dict[str, dict[str, str]] = {"keys": keys_data}
            content = json.dumps(data, indent=2, sort_keys=True)

            # Create parent directory with restrictive permissions if needed
            # Use os.makedirs with explicit mode - this is thread-safe
            parent_dir = self._key_file.parent
            if not parent_dir.exists():
                # Create with owner-only permissions (0o700)
                # exist_ok=True handles race where another thread creates it
                parent_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Atomic write: write to temp file, then rename
            # This ensures readers never see partial content
            fd = None
            temp_path = None
            try:
                # Create temp file in same directory (required for atomic rename)
                # Use os.open() with explicit O_CREAT | O_EXCL | O_WRONLY for security:
                # - O_EXCL ensures we create a new file (no symlink attacks)
                # - Explicit mode=0o600 sets permissions at creation time (thread-safe)
                fd, temp_path = tempfile.mkstemp(
                    dir=parent_dir,
                    prefix=".keys_",
                    suffix=".tmp",
                )
                # mkstemp creates with 0o600 by default, but set explicitly for clarity
                os.fchmod(fd, self._MAX_ALLOWED_MODE)

                # Write content
                os.write(fd, content.encode("utf-8"))
                os.fsync(fd)  # Ensure data is flushed to disk before rename
                os.close(fd)
                fd = None  # Mark as closed

                # Atomic rename - this is the commit point
                # On POSIX, rename() is atomic within same filesystem
                temp_path_obj = Path(temp_path)
                temp_path_obj.rename(self._key_file)
                temp_path = None  # Mark as renamed (no cleanup needed)

            except OSError:
                # Clean up temp file on failure
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass  # cleanup-resilience-ok: best effort cleanup
                if temp_path is not None:
                    try:
                        Path(temp_path).unlink()
                    except OSError:
                        pass  # cleanup-resilience-ok: best effort cleanup
                raise

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
