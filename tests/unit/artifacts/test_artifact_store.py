# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the content-addressed ArtifactStore (OMN-13093 slice; OMN-13152 Phase 1).

Covers write/read round-trips, content addressing, sharded layout, typed
sidecar metadata, idempotency, hash verification on read, fail-fast on a
missing ``ONEX_ARTIFACT_STORE_ROOT`` env var, and the Phase 1 hardening:
retention classes, quota enforcement (per-write + per-scope), redaction state +
secret detection, the restricted visibility tier, and the authorized read API
with chunked streaming.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

from omnibase_core.artifacts.artifact_store import (
    ARTIFACT_STORE_ROOT_ENV,
    RESTRICTED_ARTIFACT_KINDS,
    WRITER_VERSION,
    ArtifactQuotaExceededError,
    ArtifactSecretDetectedError,
    ArtifactStore,
    ArtifactUnauthorizedError,
    SecretDetector,
)
from omnibase_core.enums.artifacts.enum_artifact_redaction_state import (
    EnumArtifactRedactionState,
)
from omnibase_core.enums.artifacts.enum_artifact_retention_class import (
    EnumArtifactRetentionClass,
)
from omnibase_core.models.artifacts.model_artifact_auth_context import (
    ModelArtifactAuthContext,
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

    def test_negative_quota_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="max_artifact_bytes"):
            ArtifactStore(max_artifact_bytes=-1)
        with pytest.raises(ValueError, match="max_scope_bytes"):
            ArtifactStore(max_scope_bytes=-1)


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
    """Typed metadata sidecar carries the artifact-captured required fields."""

    def test_sidecar_written_next_to_blob(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        meta_path = tmp_path / ref.hex_digest[:2] / f"{ref.hex_digest}.meta.json"
        assert meta_path.is_file()

    def test_sidecar_required_fields(self, store: ArtifactStore) -> None:
        ref = _write(store)
        meta = store.read_meta(ref)
        assert meta.artifact_hash == ref.hex_digest
        assert meta.artifact_size_bytes == len(_PAYLOAD)
        assert meta.artifact_media_type == "text/plain"
        assert meta.artifact_kind == "tool_stdout"
        assert meta.source_system == "local_cli"
        assert meta.scope_ref == "omnibase_core/OMN-13093"
        assert meta.correlation_id == "11111111-2222-3333-4444-555555555555"
        assert meta.redaction_state is EnumArtifactRedactionState.RAW
        assert meta.redaction_transform is None
        assert meta.restricted is False
        assert meta.retention_class is EnumArtifactRetentionClass.SESSION
        assert meta.token_estimate > 0
        assert meta.created_at_utc.endswith("+00:00")
        assert meta.writer_version == WRITER_VERSION

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
        assert meta.scope_ref is None
        assert meta.correlation_id is None

    def test_sidecar_first_writer_wins(self, store: ArtifactStore) -> None:
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
class TestArtifactRetention:
    """Retention classes and configurable TTL."""

    def test_default_retention_class_is_session(self, store: ArtifactStore) -> None:
        ref = _write(store)
        meta = store.read_meta(ref)
        assert meta.retention_class is EnumArtifactRetentionClass.SESSION
        assert meta.retention_ttl_seconds == 24 * 60 * 60

    @pytest.mark.parametrize(
        ("retention_class", "expected_ttl"),
        [
            (EnumArtifactRetentionClass.EPHEMERAL, 3600),
            (EnumArtifactRetentionClass.SESSION, 86400),
            (EnumArtifactRetentionClass.TICKET, 90 * 86400),
            (EnumArtifactRetentionClass.PERMANENT, None),
        ],
    )
    def test_retention_class_default_ttl(
        self,
        store: ArtifactStore,
        retention_class: EnumArtifactRetentionClass,
        expected_ttl: int | None,
    ) -> None:
        ref = store.write_blob(
            f"payload-{retention_class.value}".encode(),
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
            retention_class=retention_class,
        )
        meta = store.read_meta(ref)
        assert meta.retention_class is retention_class
        assert meta.retention_ttl_seconds == expected_ttl

    def test_explicit_ttl_override(self, store: ArtifactStore) -> None:
        ref = store.write_blob(
            b"custom-ttl-payload",
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
            retention_class=EnumArtifactRetentionClass.EPHEMERAL,
            retention_ttl_seconds=42,
        )
        meta = store.read_meta(ref)
        assert meta.retention_ttl_seconds == 42


@pytest.mark.unit
class TestArtifactQuota:
    """Per-write and per-scope quota enforcement — no silent truncation."""

    def test_per_write_quota_exceeded_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        store = ArtifactStore(max_artifact_bytes=10)
        with pytest.raises(ArtifactQuotaExceededError, match="per-write quota"):
            store.write_blob(
                b"x" * 11,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )

    def test_per_write_quota_rejects_with_no_blob_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        store = ArtifactStore(max_artifact_bytes=10)
        data = b"x" * 11
        ref = ModelArtifactRef.from_bytes(data)
        with pytest.raises(ArtifactQuotaExceededError):
            store.write_blob(
                data,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )
        # No silent truncation: nothing persisted at all.
        assert not (tmp_path / ref.hex_digest[:2] / ref.hex_digest).exists()

    def test_per_write_quota_at_limit_allowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        store = ArtifactStore(max_artifact_bytes=10)
        ref = store.write_blob(
            b"x" * 10,
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
        )
        assert store.read_blob(ref) == b"x" * 10

    def test_per_scope_quota_exceeded_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        store = ArtifactStore(max_scope_bytes=20)
        store.write_blob(
            b"a" * 15,
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref="scope-A",
            correlation_id=None,
        )
        with pytest.raises(ArtifactQuotaExceededError, match="per-scope quota"):
            store.write_blob(
                b"b" * 10,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref="scope-A",
                correlation_id=None,
            )

    def test_per_scope_quota_isolated_per_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        store = ArtifactStore(max_scope_bytes=20)
        store.write_blob(
            b"a" * 15,
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref="scope-A",
            correlation_id=None,
        )
        # A different scope is unaffected by scope-A's usage.
        ref = store.write_blob(
            b"b" * 15,
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref="scope-B",
            correlation_id=None,
        )
        assert store.read_blob(ref) == b"b" * 15


@pytest.mark.unit
class TestArtifactRedactionAndSecrets:
    """Redaction state and secret-detection refusal."""

    def test_secret_detected_refuses_raw_write(self, store: ArtifactStore) -> None:
        payload = b"export AWS_KEY=AKIAIOSFODNN7EXAMPLE\n"  # pragma: allowlist secret
        with pytest.raises(ArtifactSecretDetectedError):
            store.write_blob(
                payload,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )

    def test_secret_detected_no_blob_persisted(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        payload = b"token=ghp_" + b"a" * 36 + b"\n"
        ref = ModelArtifactRef.from_bytes(payload)
        with pytest.raises(ArtifactSecretDetectedError) as exc_info:
            store.write_blob(
                payload,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )
        assert exc_info.value.ref == ref
        # No blob bytes on disk.
        assert not (tmp_path / ref.hex_digest[:2] / ref.hex_digest).exists()
        # But an auditable secret_detected sidecar IS recorded.
        meta = store.read_meta(ref)
        assert meta.redaction_state is EnumArtifactRedactionState.SECRET_DETECTED

    def test_secret_detected_blob_read_fails_missing(
        self, store: ArtifactStore
    ) -> None:
        payload = b"token=ghp_" + b"b" * 36 + b"\n"
        ref = ModelArtifactRef.from_bytes(payload)
        with pytest.raises(ArtifactSecretDetectedError):
            store.write_blob(
                payload,
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )
        # The blob never existed, so a read fails explicitly.
        with pytest.raises(FileNotFoundError):
            store.read(ref)

    def test_redaction_transform_records_itself(self, store: ArtifactStore) -> None:
        def _strip(_data: bytes) -> bytes:
            return b"[REDACTED]"

        ref = store.write_blob(
            b"sensitive original content",
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
            redaction_transform=_strip,
            redaction_transform_name="strip_all_v1",
        )
        meta = store.read_meta(ref)
        assert meta.redaction_state is EnumArtifactRedactionState.REDACTED
        assert meta.redaction_transform == "strip_all_v1"
        # The STORED bytes are the transform output, content-addressed.
        assert store.read_blob(ref) == b"[REDACTED]"
        assert ref == ModelArtifactRef.from_bytes(b"[REDACTED]")

    def test_redaction_transform_requires_name(self, store: ArtifactStore) -> None:
        with pytest.raises(ValueError, match="redaction_transform_name"):
            store.write_blob(
                b"data",
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
                redaction_transform=lambda d: d,
            )

    def test_custom_secret_detector(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ARTIFACT_STORE_ROOT_ENV, str(tmp_path))
        detector = SecretDetector(patterns=(re.compile(rb"TOPSECRET"),))
        store = ArtifactStore(secret_detector=detector)
        with pytest.raises(ArtifactSecretDetectedError):
            store.write_blob(
                b"this is TOPSECRET data",
                media_type="text/plain",
                artifact_kind="tool_stdout",
                source_system="local_cli",
                scope_ref=None,
                correlation_id=None,
            )


@pytest.mark.unit
class TestArtifactRestrictedTier:
    """Restricted visibility tier + authorized read gate."""

    def test_restricted_kinds_default_to_restricted(self, store: ArtifactStore) -> None:
        for kind in RESTRICTED_ARTIFACT_KINDS:
            ref = store.write_blob(
                f"body-{kind}".encode(),
                media_type="text/plain",
                artifact_kind=kind,
                source_system="claude_code",
                scope_ref=None,
                correlation_id=None,
            )
            assert store.read_meta(ref).restricted is True

    def test_unrestricted_kind_not_restricted(self, store: ArtifactStore) -> None:
        ref = _write(store)
        assert store.read_meta(ref).restricted is False

    def test_restricted_read_without_auth_raises(self, store: ArtifactStore) -> None:
        ref = store.write_blob(
            b"session body",
            media_type="text/plain",
            artifact_kind="session_transcript",
            source_system="claude_code",
            scope_ref=None,
            correlation_id=None,
        )
        with pytest.raises(ArtifactUnauthorizedError):
            store.read(ref)

    def test_restricted_read_with_wrong_kind_auth_raises(
        self, store: ArtifactStore
    ) -> None:
        ref = store.write_blob(
            b"session body",
            media_type="text/plain",
            artifact_kind="session_transcript",
            source_system="claude_code",
            scope_ref=None,
            correlation_id=None,
        )
        auth = ModelArtifactAuthContext(
            principal="agent-x",
            authorized_kinds=frozenset({"hook_trace"}),
        )
        with pytest.raises(ArtifactUnauthorizedError):
            store.read(ref, auth_context=auth)

    def test_restricted_read_with_auth_succeeds(self, store: ArtifactStore) -> None:
        body = b"session body content"
        ref = store.write_blob(
            body,
            media_type="text/plain",
            artifact_kind="session_transcript",
            source_system="claude_code",
            scope_ref=None,
            correlation_id=None,
        )
        auth = ModelArtifactAuthContext(
            principal="agent-x",
            authorized_kinds=frozenset({"session_transcript"}),
        )
        assert store.read(ref, auth_context=auth) == body

    def test_unrestricted_read_needs_no_auth(self, store: ArtifactStore) -> None:
        ref = _write(store)
        assert store.read(ref) == _PAYLOAD

    def test_explicit_restricted_override_on_unrestricted_kind(
        self, store: ArtifactStore
    ) -> None:
        ref = store.write_blob(
            b"normally open",
            media_type="text/plain",
            artifact_kind="tool_stdout",
            source_system="local_cli",
            scope_ref=None,
            correlation_id=None,
            restricted=True,
        )
        assert store.read_meta(ref).restricted is True
        with pytest.raises(ArtifactUnauthorizedError):
            store.read(ref)


@pytest.mark.unit
class TestArtifactStoreRead:
    """Hash-verified retrieval, missing-artifact, streaming."""

    def test_read_roundtrip(self, store: ArtifactStore) -> None:
        ref = _write(store)
        assert store.read(ref) == _PAYLOAD

    def test_read_large_payload(self, store: ArtifactStore) -> None:
        data = b"x" * 100_000
        ref = _write(store, data)
        assert store.read(ref) == data

    def test_read_missing_raises(self, store: ArtifactStore) -> None:
        ref = ModelArtifactRef.from_bytes(b"never written")
        with pytest.raises(FileNotFoundError):
            store.read(ref)

    def test_read_blob_missing_raises(self, store: ArtifactStore) -> None:
        ref = ModelArtifactRef.from_bytes(b"never written")
        with pytest.raises(FileNotFoundError):
            store.read_blob(ref)

    def test_read_detects_corruption(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        blob_path = tmp_path / ref.hex_digest[:2] / ref.hex_digest
        blob_path.write_bytes(b"tampered bytes")
        with pytest.raises(ValueError, match="hash mismatch"):
            store.read(ref)

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

    def test_read_chunks_roundtrip(self, store: ArtifactStore) -> None:
        data = b"y" * 200_000
        ref = _write(store, data)
        chunks = b"".join(store.read_chunks(ref, chunk_size=64 * 1024))
        assert chunks == data

    def test_read_chunks_restricted_auth_enforced(self, store: ArtifactStore) -> None:
        ref = store.write_blob(
            b"hook trace body",
            media_type="text/plain",
            artifact_kind="hook_trace",
            source_system="claude_code",
            scope_ref=None,
            correlation_id=None,
        )
        with pytest.raises(ArtifactUnauthorizedError):
            list(store.read_chunks(ref))

    def test_read_chunks_detects_corruption(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        ref = _write(store)
        blob_path = tmp_path / ref.hex_digest[:2] / ref.hex_digest
        blob_path.write_bytes(b"tampered")
        with pytest.raises(ValueError, match="hash mismatch"):
            list(store.read_chunks(ref))

    def test_read_chunks_rejects_nonpositive_chunk_size(
        self, store: ArtifactStore
    ) -> None:
        ref = _write(store)
        with pytest.raises(ValueError, match="chunk_size"):
            list(store.read_chunks(ref, chunk_size=0))


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
        assert store.read(ref) == b"x" * 100_000
        assert ref.ref.startswith("sha256:")
