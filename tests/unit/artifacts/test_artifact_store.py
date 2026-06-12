# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the minimal content-addressed ArtifactStore slice (OMN-13093).

Covers write/read round-trips, content addressing, sharded layout, sidecar
metadata, idempotency, hash verification on read, and fail-fast behavior on
a missing ``ONEX_ARTIFACT_STORE_ROOT`` env var.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from omnibase_core.artifacts.artifact_store import (
    ARTIFACT_STORE_ROOT_ENV,
    WRITER_VERSION,
    ArtifactStore,
)
from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

_PAYLOAD = b"runtime capture log line\n" * 100


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ArtifactStore:
    """ArtifactStore rooted at a per-test temp directory."""
    monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
    return ArtifactStore()


def _write(store: ArtifactStore, data: bytes = _PAYLOAD) -> ModelArtifactRef:
    return store.write_blob(
        data,
        media_type="text/plain",
        artifact_kind="tool_stdout",
        source_system="local_cli",
        scope_ref="omnibase_core/OMN-13093",
        correlation_id="11111111-2222-3333-4444-555555555555",
    )


@pytest.mark.unit
class TestArtifactStoreEnv:
    """Fail-fast store-root resolution (Operating Rule 8)."""

    def test_missing_env_raises_keyerror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ARTIFACT_STORE_ROOT_ENV, raising=False)
        with pytest.raises(KeyError):
            ArtifactStore()

    def test_root_created_lazily_on_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "not-yet-created" / "artifacts"
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(root))
        store = ArtifactStore()
        ref = _write(store)
        assert (root / ref.hex_digest[:2] / ref.hex_digest).is_file()


@pytest.mark.unit
class TestArtifactStoreWrite:
    """Content addressing, sharded layout, atomic writes."""

    def test_write_returns_content_address(self, store: ArtifactStore) -> None:
        ref = _write(store)
        assert ref.ref == f"sha256:{hashlib.sha256(_PAYLOAD).hexdigest()}"

    def test_blob_stored_at_sharded_path(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        blob_path = tmp_path / ref.hex_digest[:2] / ref.hex_digest
        assert blob_path.is_file()
        assert blob_path.read_bytes() == _PAYLOAD

    def test_no_temp_files_left_behind(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        shard = tmp_path / ref.hex_digest[:2]
        leftovers = [
            p
            for p in shard.iterdir()
            if p.name not in {ref.hex_digest, f"{ref.hex_digest}.meta.json"}
        ]
        assert leftovers == []

    def test_write_is_idempotent_on_existing_hash(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref_first = _write(store)
        blob_path = tmp_path / ref_first.hex_digest[:2] / ref_first.hex_digest
        first_stat = blob_path.stat()
        ref_second = _write(store)
        assert ref_second == ref_first
        # The existing blob is not rewritten.
        second_stat = blob_path.stat()
        assert second_stat.st_mtime_ns == first_stat.st_mtime_ns
        assert second_stat.st_ino == first_stat.st_ino

    def test_distinct_payloads_get_distinct_refs(self, store: ArtifactStore) -> None:
        ref_a = _write(store, b"a")
        ref_b = _write(store, b"b")
        assert ref_a != ref_b

    def test_empty_payload_supported(self, store: ArtifactStore) -> None:
        ref = _write(store, b"")
        assert store.read_blob(ref) == b""


@pytest.mark.unit
class TestArtifactStoreSidecar:
    """JSON metadata sidecar carries the artifact-captured required fields."""

    def test_sidecar_written_next_to_blob(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        meta_path = tmp_path / ref.hex_digest[:2] / f"{ref.hex_digest}.meta.json"
        assert meta_path.is_file()

    def test_sidecar_required_fields(self, store: ArtifactStore) -> None:
        ref = _write(store)
        meta = store.read_meta(ref)
        assert meta["artifact_hash"] == ref.hex_digest
        assert meta["artifact_size_bytes"] == len(_PAYLOAD)
        assert meta["artifact_media_type"] == "text/plain"
        assert meta["artifact_kind"] == "tool_stdout"
        assert meta["source_system"] == "local_cli"
        assert meta["scope_ref"] == "omnibase_core/OMN-13093"
        assert meta["correlation_id"] == "11111111-2222-3333-4444-555555555555"
        assert meta["redaction_state"] == "raw"
        assert isinstance(meta["token_estimate"], int)
        assert meta["token_estimate"] > 0
        assert isinstance(meta["created_at_utc"], str)
        assert meta["created_at_utc"].endswith("+00:00")
        assert meta["writer_version"] == WRITER_VERSION

    def test_sidecar_none_fields_serialized_as_null(self, store: ArtifactStore) -> None:
        ref = store.write_blob(
            b"payload-with-no-scope",
            media_type="application/json",
            artifact_kind="tool_result_json",
            source_system="onex_node",
            scope_ref=None,
            correlation_id=None,
        )
        meta = store.read_meta(ref)
        assert meta["scope_ref"] is None
        assert meta["correlation_id"] is None

    def test_sidecar_first_writer_wins(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        first_meta = store.read_meta(ref)
        # Re-write same bytes with different metadata: blob is idempotent and
        # the original sidecar is preserved.
        store.write_blob(
            _PAYLOAD,
            media_type="text/x-diff",
            artifact_kind="diff",
            source_system="claude_code",
            scope_ref=None,
            correlation_id=None,
        )
        assert store.read_meta(ref) == first_meta


@pytest.mark.unit
class TestArtifactStoreRead:
    """Hash-verified retrieval."""

    def test_read_blob_roundtrip(self, store: ArtifactStore) -> None:
        ref = _write(store)
        assert store.read_blob(ref) == _PAYLOAD

    def test_read_blob_large_payload(self, store: ArtifactStore) -> None:
        data = b"x" * 100_000
        ref = _write(store, data)
        assert store.read_blob(ref) == data

    def test_read_blob_missing_raises(self, store: ArtifactStore) -> None:
        ref = ModelArtifactRef.from_bytes(b"never written")
        with pytest.raises(FileNotFoundError):
            store.read_blob(ref)

    def test_read_blob_detects_corruption(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        blob_path = tmp_path / ref.hex_digest[:2] / ref.hex_digest
        blob_path.write_bytes(b"tampered bytes")
        with pytest.raises(ValueError, match="hash mismatch"):
            store.read_blob(ref)

    def test_read_meta_missing_raises(self, store: ArtifactStore) -> None:
        ref = ModelArtifactRef.from_bytes(b"never written")
        with pytest.raises(FileNotFoundError):
            store.read_meta(ref)


@pytest.mark.unit
class TestAcceptanceProbe:
    """Mirror of the ticket's acceptance probe."""

    def test_probe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        assert os.environ[ARTIFACT_STORE_ROOT_ENV] == str(tmp_path)
        store = ArtifactStore()
        ref = store.write_blob(
            b"x" * 100_000,
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
        )
        assert store.read_blob(ref) == b"x" * 100_000
        assert ref.ref.startswith("sha256:")
