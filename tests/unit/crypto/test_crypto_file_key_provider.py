"""Unit tests for FileKeyProvider."""

from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair
from omnibase_core.crypto.crypto_file_key_provider import FileKeyProvider
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.fixture
def temp_key_file(tmp_path: Path) -> Path:
    """Create a temporary key file path."""
    return tmp_path / "runtime_keys.json"


@pytest.fixture
def provider(temp_key_file: Path) -> FileKeyProvider:
    """Create a FileKeyProvider with a temp file."""
    return FileKeyProvider(temp_key_file)


@pytest.mark.unit
class TestFileKeyProviderBasics:
    """Basic functionality tests."""

    def test_init_creates_empty_provider(self, provider: FileKeyProvider) -> None:
        """New provider starts with no keys."""
        assert provider.list_runtime_ids() == []

    def test_register_key_success(self, provider: FileKeyProvider) -> None:
        """Can register a valid public key."""
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)
        assert provider.has_key("runtime-001") is True

    def test_register_key_invalid_length(self, provider: FileKeyProvider) -> None:
        """Raises ValueError for invalid key length."""
        with pytest.raises(ValueError, match="must be 32 bytes"):
            provider.register_key("runtime-001", b"too short")

    def test_get_public_key_found(self, provider: FileKeyProvider) -> None:
        """get_public_key returns key when found."""
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)
        result = provider.get_public_key("runtime-001")
        assert result == keypair.public_key_bytes

    def test_get_public_key_not_found(self, provider: FileKeyProvider) -> None:
        """get_public_key returns None when not found."""
        assert provider.get_public_key("unknown-runtime") is None

    def test_has_key_true(self, provider: FileKeyProvider) -> None:
        """has_key returns True when key exists."""
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)
        assert provider.has_key("runtime-001") is True

    def test_has_key_false(self, provider: FileKeyProvider) -> None:
        """has_key returns False when key doesn't exist."""
        assert provider.has_key("unknown-runtime") is False

    def test_list_runtime_ids(self, provider: FileKeyProvider) -> None:
        """list_runtime_ids returns all registered runtimes."""
        keypair1 = generate_keypair()
        keypair2 = generate_keypair()
        provider.register_key("runtime-001", keypair1.public_key_bytes)
        provider.register_key("runtime-002", keypair2.public_key_bytes)
        runtime_ids = provider.list_runtime_ids()
        assert set(runtime_ids) == {"runtime-001", "runtime-002"}


@pytest.mark.unit
class TestFileKeyProviderPersistence:
    """Persistence and file handling tests."""

    def test_keys_persisted_to_file(
        self, temp_key_file: Path, provider: FileKeyProvider
    ) -> None:
        """Keys are saved to file."""
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)

        # Verify file exists and has content
        assert temp_key_file.exists()
        data = json.loads(temp_key_file.read_text())
        assert "keys" in data
        assert "runtime-001" in data["keys"]

    def test_keys_loaded_from_existing_file(self, temp_key_file: Path) -> None:
        """Keys are loaded from existing file on init."""
        keypair = generate_keypair()

        # Create provider and register key
        provider1 = FileKeyProvider(temp_key_file)
        provider1.register_key("runtime-001", keypair.public_key_bytes)

        # Create new provider instance - should load existing keys
        provider2 = FileKeyProvider(temp_key_file)
        assert provider2.has_key("runtime-001") is True
        assert provider2.get_public_key("runtime-001") == keypair.public_key_bytes

    def test_reload_picks_up_changes(self, temp_key_file: Path) -> None:
        """reload() picks up external changes to file."""
        provider = FileKeyProvider(temp_key_file)
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)

        # Simulate external modification
        keypair2 = generate_keypair()
        data = {
            "keys": {
                "runtime-002": base64.urlsafe_b64encode(
                    keypair2.public_key_bytes
                ).decode()
            }
        }
        temp_key_file.write_text(json.dumps(data))

        # Before reload, old data
        assert provider.has_key("runtime-001") is True
        assert provider.has_key("runtime-002") is False

        # After reload, new data
        provider.reload()
        assert provider.has_key("runtime-001") is False
        assert provider.has_key("runtime-002") is True

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Provider handles missing file gracefully."""
        key_file = tmp_path / "nonexistent" / "keys.json"
        provider = FileKeyProvider(key_file)
        assert provider.list_runtime_ids() == []

        # Can still register keys (creates file)
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)
        assert key_file.exists()

    def test_handles_corrupt_file_gracefully(self, temp_key_file: Path) -> None:
        """Provider handles corrupt file by starting fresh."""
        temp_key_file.write_text("not valid json {{{")
        temp_key_file.chmod(0o600)  # Set secure permissions
        provider = FileKeyProvider(temp_key_file)
        assert provider.list_runtime_ids() == []


@pytest.mark.unit
class TestFileKeyProviderRemoval:
    """Key removal tests."""

    def test_remove_key_success(self, provider: FileKeyProvider) -> None:
        """remove_key removes existing key."""
        keypair = generate_keypair()
        provider.register_key("runtime-001", keypair.public_key_bytes)
        assert provider.remove_key("runtime-001") is True
        assert provider.has_key("runtime-001") is False

    def test_remove_key_not_found(self, provider: FileKeyProvider) -> None:
        """remove_key returns False for non-existent key."""
        assert provider.remove_key("unknown") is False


@pytest.mark.unit
class TestFileKeyProviderProtocolCompliance:
    """Verify ProtocolKeyProvider compliance."""

    def test_implements_protocol(self, provider: FileKeyProvider) -> None:
        """FileKeyProvider implements ProtocolKeyProvider."""
        from omnibase_core.protocols.crypto.protocol_key_provider import (
            ProtocolKeyProvider,
        )

        assert isinstance(provider, ProtocolKeyProvider)


@pytest.mark.unit
class TestFileKeyProviderThreadSafety:
    """Thread safety tests."""

    def test_concurrent_register_and_get(self, temp_key_file: Path) -> None:
        """Concurrent register and get operations don't corrupt state."""
        import threading

        provider = FileKeyProvider(temp_key_file)
        errors: list[Exception] = []
        num_threads = 10
        keys_per_thread = 5

        def register_keys(thread_id: int) -> None:
            try:
                for i in range(keys_per_thread):
                    keypair = generate_keypair()
                    runtime_id = f"runtime-{thread_id}-{i}"
                    provider.register_key(runtime_id, keypair.public_key_bytes)
                    # Immediately verify it was registered
                    assert provider.has_key(runtime_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_keys, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should have occurred
        assert errors == [], f"Thread errors: {errors}"

        # All keys should be registered
        runtime_ids = provider.list_runtime_ids()
        expected_count = num_threads * keys_per_thread
        assert len(runtime_ids) == expected_count


@pytest.mark.unit
class TestFileKeyProviderFilePermissions:
    """File permission validation tests (fail-closed security)."""

    def _create_key_file_with_permissions(self, key_file: Path, mode: int) -> None:
        """Helper to create a key file with specific permissions."""
        keypair = generate_keypair()
        data = {
            "keys": {
                "test-runtime": base64.urlsafe_b64encode(
                    keypair.public_key_bytes
                ).decode()
            }
        }
        key_file.write_text(json.dumps(data))
        key_file.chmod(mode)

    def test_secure_permissions_accepted(self, temp_key_file: Path) -> None:
        """File with secure permissions (0o600) loads successfully."""
        self._create_key_file_with_permissions(temp_key_file, 0o600)
        provider = FileKeyProvider(temp_key_file)
        assert provider.has_key("test-runtime") is True

    def test_owner_read_only_accepted(self, temp_key_file: Path) -> None:
        """File with owner read-only (0o400) loads successfully."""
        self._create_key_file_with_permissions(temp_key_file, 0o400)
        provider = FileKeyProvider(temp_key_file)
        assert provider.has_key("test-runtime") is True

    def test_group_readable_rejected(self, temp_key_file: Path) -> None:
        """File with group read permission (0o640) raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o640)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "group/other access bits" in str(exc_info.value.message)

    def test_group_writable_rejected(self, temp_key_file: Path) -> None:
        """File with group write permission (0o660) raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o660)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "group/other access bits" in str(exc_info.value.message)

    def test_world_readable_rejected(self, temp_key_file: Path) -> None:
        """File with world read permission (0o644) raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o644)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "group/other access bits" in str(exc_info.value.message)

    def test_world_writable_rejected(self, temp_key_file: Path) -> None:
        """File with world write permission (0o666) raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o666)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "group/other access bits" in str(exc_info.value.message)

    def test_fully_open_rejected(self, temp_key_file: Path) -> None:
        """File with fully open permissions (0o777) raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o777)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "group/other access bits" in str(exc_info.value.message)

    @pytest.mark.skipif(
        os.geteuid() == 0,
        reason="Cannot test setuid/setgid as root - permissions are bypassed",
    )
    def test_setuid_bit_rejected(self, temp_key_file: Path) -> None:
        """File with setuid bit raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o600)
        # Add setuid bit
        current_mode = temp_key_file.stat().st_mode
        temp_key_file.chmod(current_mode | stat.S_ISUID)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "setuid" in str(exc_info.value.message)

    @pytest.mark.skipif(
        os.geteuid() == 0,
        reason="Cannot test setuid/setgid as root - permissions are bypassed",
    )
    def test_setgid_bit_rejected(self, temp_key_file: Path) -> None:
        """File with setgid bit raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o600)
        # Add setgid bit
        current_mode = temp_key_file.stat().st_mode
        temp_key_file.chmod(current_mode | stat.S_ISGID)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "setgid" in str(exc_info.value.message)

    def test_sticky_bit_rejected(self, temp_key_file: Path) -> None:
        """File with sticky bit raises ModelOnexError."""
        self._create_key_file_with_permissions(temp_key_file, 0o600)
        # Add sticky bit
        current_mode = temp_key_file.stat().st_mode
        temp_key_file.chmod(current_mode | stat.S_ISVTX)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert exc_info.value.error_code == EnumCoreErrorCode.PERMISSION_ERROR
        assert "sticky" in str(exc_info.value.message)

    def test_error_context_contains_file_path(self, temp_key_file: Path) -> None:
        """Error context includes file path for debugging."""
        self._create_key_file_with_permissions(temp_key_file, 0o644)
        with pytest.raises(ModelOnexError) as exc_info:
            FileKeyProvider(temp_key_file)
        assert "file_path" in exc_info.value.context
        assert str(temp_key_file) in exc_info.value.context["file_path"]


@pytest.mark.unit
class TestFileKeyProviderValidation:
    """Key validation tests."""

    def test_skips_invalid_length_keys_on_load(self, temp_key_file: Path) -> None:
        """Keys with invalid length are skipped when loading from file."""
        # Create file with one valid and one invalid key
        valid_key = generate_keypair().public_key_bytes
        invalid_key = b"too short"

        data = {
            "keys": {
                "valid-runtime": base64.urlsafe_b64encode(valid_key).decode(),
                "invalid-runtime": base64.urlsafe_b64encode(invalid_key).decode(),
            }
        }
        temp_key_file.write_text(json.dumps(data))
        temp_key_file.chmod(0o600)  # Set secure permissions

        # Load provider - should skip invalid key
        provider = FileKeyProvider(temp_key_file)
        assert provider.has_key("valid-runtime") is True
        assert provider.has_key("invalid-runtime") is False
        assert provider.get_public_key("valid-runtime") == valid_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
