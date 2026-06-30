# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact store (OMN-13093 minimal slice; OMN-13152 Phase 1).

Blobs are stored under ``$ONEX_ARTIFACT_STORE_ROOT`` at the sharded path
``<root>/<hh>/<full-hex>`` where ``<hh>`` is the first two hex chars of the
blob's SHA-256 digest. Every blob carries a JSON metadata sidecar
``<full-hex>.meta.json`` typed by :class:`ModelArtifactMetadata`.

Phase 1 hardening (OMN-13152) added in place:

- **Retention classes** (:class:`EnumArtifactRetentionClass`) with a
  configurable TTL per class, recorded on the sidecar.
- **Quota enforcement**: a max per-write size and a max total store size per
  scope. Exceeding either raises :class:`ArtifactQuotaExceededError` — there is
  no silent truncation or partial write.
- **Redaction state** (:class:`EnumArtifactRedactionState`) on the sidecar. On
  secret detection the store sets ``secret_detected`` and refuses the raw
  write; an applied redaction transform records itself on the sidecar.
- **Restricted visibility tier**: ``session_transcript`` and ``hook_trace``
  artifact kinds are restricted by default; :meth:`read` requires an authorized
  :class:`ModelArtifactAuthContext`.
- **Hardened read**: :meth:`read` hash-verifies on every read, enforces the
  restricted-topic auth gate, exposes the redaction state, supports chunked
  streaming, and raises explicitly on a missing artifact.

Design constraints (unchanged from the minimal slice):

- stdlib + Pydantic only — no infra deps — so omniclaude hooks import this
  module cleanly (layering rule 7 / F14)
- store root from ``os.environ["ONEX_ARTIFACT_STORE_ROOT"]`` — required env,
  ``KeyError`` on absence (fail-fast, Operating Rule 8)
- atomic temp+rename writes, idempotent on existing hash
- reads are hash-verified against the content address

.. versionadded:: OMN-13093
.. versionchanged:: OMN-13152
   Retention, quota, redaction, restricted-tier read auth, typed sidecar.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.enums.artifacts.enum_artifact_redaction_state import (
    EnumArtifactRedactionState,
)
from omnibase_core.enums.artifacts.enum_artifact_retention_class import (
    EnumArtifactRetentionClass,
)
from omnibase_core.models.artifacts.model_artifact_auth_context import (
    ModelArtifactAuthContext,
)
from omnibase_core.models.artifacts.model_artifact_metadata import (
    ModelArtifactMetadata,
)
from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

__all__ = [
    "ARTIFACT_STORE_ROOT_ENV",
    "DEFAULT_READ_CHUNK_BYTES",
    "RESTRICTED_ARTIFACT_KINDS",
    "WRITER_VERSION",
    "ArtifactQuotaExceededError",
    "ArtifactSecretDetectedError",
    "ArtifactStore",
    "ArtifactUnauthorizedError",
    "SecretDetector",
]

ARTIFACT_STORE_ROOT_ENV = "ONEX_ARTIFACT_STORE_ROOT"

# Sidecar generation marker. Bumped from the minimal slice now that the sidecar
# is typed and carries retention/redaction/visibility fields.
WRITER_VERSION = "omn-13152-phase1-1"

# Crude byte-based token estimate (~4 bytes/token for English-ish text).
# Good enough for projection previews and budget heuristics; NOT a tokenizer.
_BYTES_PER_TOKEN_ESTIMATE = 4

_META_SUFFIX = ".meta.json"

# Default chunk size for streaming reads.
DEFAULT_READ_CHUNK_BYTES = 64 * 1024

# Artifact kinds whose reads are restricted by default (require auth_context).
RESTRICTED_ARTIFACT_KINDS: frozenset[str] = frozenset(
    {"session_transcript", "hook_trace"}
)

# A redaction transform is a pure ``bytes -> bytes`` callable returning the
# sanitized bytes. It identifies itself via a name passed alongside.
RedactionTransform = Callable[[bytes], bytes]


class ArtifactQuotaExceededError(Exception):
    """Raised when a write would exceed a per-write or per-scope size quota.

    No bytes are persisted when this is raised — the write fails closed with no
    silent truncation.
    """


class ArtifactSecretDetectedError(Exception):
    """Raised when a secret is detected in bytes submitted for a raw write.

    The raw bytes are refused and never persisted; a ``secret_detected``
    sidecar is recorded instead so the detection is auditable.
    """

    def __init__(self, ref: ModelArtifactRef) -> None:
        self.ref = ref
        super().__init__(
            f"secret detected in artifact {ref.ref}; raw write refused "
            "(secret_detected sidecar recorded)"
        )


class ArtifactUnauthorizedError(Exception):
    """Raised when a restricted artifact is read without sufficient authorization."""


# Default secret patterns. Deliberately conservative — high-signal token shapes
# only — so the gate does not false-positive on ordinary tool output.
_DEFAULT_SECRET_PATTERNS: tuple[re.Pattern[bytes], ...] = (
    re.compile(rb"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM private key
    re.compile(rb"ghp_[0-9A-Za-z]{36}"),  # GitHub personal access token
    re.compile(rb"xox[baprs]-[0-9A-Za-z-]{10,}"),  # Slack token
    re.compile(rb"sk-[0-9A-Za-z]{20,}"),  # OpenAI-style secret key
)


class SecretDetector:
    """Pattern-based secret detector for the raw-write gate.

    Stateless and deterministic. Callers may supply their own patterns; the
    default set targets high-signal credential shapes only.
    """

    def __init__(self, patterns: tuple[re.Pattern[bytes], ...] | None = None) -> None:
        self._patterns = patterns if patterns is not None else _DEFAULT_SECRET_PATTERNS

    def contains_secret(self, data: bytes) -> bool:
        """Return whether ``data`` matches any configured secret pattern."""
        return any(pattern.search(data) for pattern in self._patterns)


class ArtifactStore:
    """Content-addressed blob store with typed metadata sidecars.

    The blob's :class:`ModelArtifactRef` (``sha256:<hex>``) is both its
    identity and its integrity proof: :meth:`read` re-hashes the bytes on
    retrieval and fails on mismatch.
    """

    def __init__(
        self,
        *,
        max_artifact_bytes: int | None = None,
        max_scope_bytes: int | None = None,
        secret_detector: SecretDetector | None = None,
    ) -> None:
        # Fail-fast: KeyError when ONEX_ARTIFACT_STORE_ROOT is unset.
        # No silent default — a wrong default is worse than a loud crash.
        self._root = Path(os.environ[ARTIFACT_STORE_ROOT_ENV])
        if max_artifact_bytes is not None and max_artifact_bytes < 0:
            msg = f"max_artifact_bytes must be >= 0, got {max_artifact_bytes}"
            raise ValueError(msg)
        if max_scope_bytes is not None and max_scope_bytes < 0:
            msg = f"max_scope_bytes must be >= 0, got {max_scope_bytes}"
            raise ValueError(msg)
        self._max_artifact_bytes = max_artifact_bytes
        self._max_scope_bytes = max_scope_bytes
        self._secret_detector = secret_detector or SecretDetector()

    @property
    def root(self) -> Path:
        """The store root directory (from ``ONEX_ARTIFACT_STORE_ROOT``)."""
        return self._root

    def write_blob(
        self,
        data: bytes,
        *,
        media_type: str,
        artifact_kind: str,
        source_system: str,
        scope_ref: str | None,
        correlation_id: str | None,
        retention_class: EnumArtifactRetentionClass = EnumArtifactRetentionClass.SESSION,
        retention_ttl_seconds: int | None = None,
        redaction_transform: RedactionTransform | None = None,
        redaction_transform_name: str | None = None,
        restricted: bool | None = None,
    ) -> ModelArtifactRef:
        """Store ``data`` content-addressed and return its ref.

        Writes are atomic (temp file + ``os.replace``) and idempotent: a blob
        with an existing hash is not rewritten (first writer wins for metadata).

        Hardening:

        - Quota: enforced against ``max_artifact_bytes`` and ``max_scope_bytes``
          (per ``scope_ref``) before any bytes are written. Exceeding either
          raises :class:`ArtifactQuotaExceededError`.
        - Secret detection: runs on the bytes the store would persist (after any
          redaction transform). On detection the store records a
          ``secret_detected`` sidecar and raises
          :class:`ArtifactSecretDetectedError` — raw bytes are never written.
        - Redaction: if ``redaction_transform`` is given it is applied and the
          stored bytes are the transformed bytes; the sidecar records
          ``redacted`` state and the transform name.
        - Restricted tier: defaults to True for restricted artifact kinds;
          ``restricted`` overrides explicitly.

        Raises:
            ArtifactQuotaExceededError: a quota would be exceeded.
            ArtifactSecretDetectedError: a secret was detected in the bytes.
            ValueError: redaction_transform supplied without a name.
        """
        if redaction_transform is not None and not redaction_transform_name:
            msg = "redaction_transform_name is required when redaction_transform is set"
            raise ValueError(msg)

        if redaction_transform is not None:
            stored_bytes = redaction_transform(data)
            redaction_state = EnumArtifactRedactionState.REDACTED
            transform_name = redaction_transform_name
        else:
            stored_bytes = data
            redaction_state = EnumArtifactRedactionState.RAW
            transform_name = None

        is_restricted = (
            restricted
            if restricted is not None
            else artifact_kind in RESTRICTED_ARTIFACT_KINDS
        )

        # Quota: per-write cap is checked first so an oversize single write is
        # rejected even when the scope is otherwise empty.
        self._enforce_per_write_quota(stored_bytes)

        # Secret detection runs on the bytes that would be persisted.
        if self._secret_detector.contains_secret(stored_bytes):
            secret_ref = ModelArtifactRef.from_bytes(stored_bytes)
            self._record_secret_detected(
                secret_ref,
                media_type=media_type,
                artifact_kind=artifact_kind,
                source_system=source_system,
                scope_ref=scope_ref,
                correlation_id=correlation_id,
                retention_class=retention_class,
                retention_ttl_seconds=retention_ttl_seconds,
                restricted=is_restricted,
                size_bytes=len(stored_bytes),
            )
            raise ArtifactSecretDetectedError(secret_ref)

        ref = ModelArtifactRef.from_bytes(stored_bytes)
        blob_path = self._blob_path(ref)
        if blob_path.exists():
            return ref

        # Per-scope quota is checked against the live on-disk size, immediately
        # before the write, so concurrent growth is accounted for.
        self._enforce_scope_quota(scope_ref, len(stored_bytes))

        shard_dir = blob_path.parent
        shard_dir.mkdir(parents=True, exist_ok=True)

        effective_ttl = (
            retention_ttl_seconds
            if retention_ttl_seconds is not None
            else retention_class.default_ttl_seconds
        )

        meta = ModelArtifactMetadata(
            artifact_hash=ref.hex_digest,
            artifact_size_bytes=len(stored_bytes),
            artifact_media_type=media_type,
            artifact_kind=artifact_kind,
            source_system=source_system,
            scope_ref=scope_ref,
            correlation_id=correlation_id,
            retention_class=retention_class,
            retention_ttl_seconds=effective_ttl,
            redaction_state=redaction_state,
            redaction_transform=transform_name,
            restricted=is_restricted,
            token_estimate=len(stored_bytes) // _BYTES_PER_TOKEN_ESTIMATE,
            created_at_utc=datetime.now(UTC).isoformat(),
            writer_version=WRITER_VERSION,
        )

        # Sidecar first, blob last: blob presence is the idempotency signal, so
        # a crash between the two writes never yields a blob without meta.
        self._atomic_write(self._meta_path(ref), self._serialize_meta(meta))
        self._atomic_write(blob_path, stored_bytes)
        return ref

    def read(
        self,
        artifact_ref: ModelArtifactRef,
        *,
        auth_context: ModelArtifactAuthContext | None = None,
    ) -> bytes:
        """Return the blob bytes for ``artifact_ref``, fully gated.

        On every read: the sidecar is loaded, the restricted-tier auth gate is
        enforced, the bytes are hash-verified against the ref, and the bytes are
        returned. Reading a ``secret_detected`` artifact is impossible because
        no blob was ever persisted for it.

        Raises:
            FileNotFoundError: no blob/sidecar exists for ``artifact_ref``.
            ArtifactUnauthorizedError: artifact is restricted and ``auth_context``
                does not authorize its kind.
            ValueError: stored bytes do not hash to ``artifact_ref`` (corruption).
        """
        meta = self.read_meta(artifact_ref)
        self._enforce_read_auth(artifact_ref, meta, auth_context)

        blob_path = self._blob_path(artifact_ref)
        if not blob_path.is_file():
            msg = f"no artifact blob for {artifact_ref.ref}"
            raise FileNotFoundError(msg)
        data = blob_path.read_bytes()
        self._verify_hash(artifact_ref, data)
        return data

    def read_chunks(
        self,
        artifact_ref: ModelArtifactRef,
        *,
        auth_context: ModelArtifactAuthContext | None = None,
        chunk_size: int = DEFAULT_READ_CHUNK_BYTES,
    ) -> Iterator[bytes]:
        """Stream the blob for ``artifact_ref`` in ``chunk_size`` byte chunks.

        Applies the same restricted-tier auth gate as :meth:`read`, then yields
        chunks while hash-verifying the full stream. The final hash check
        happens after the last chunk; a mismatch raises :class:`ValueError`
        once the stream is exhausted.

        Raises:
            FileNotFoundError: no blob/sidecar exists for ``artifact_ref``.
            ArtifactUnauthorizedError: artifact is restricted and unauthorized.
            ValueError: ``chunk_size`` <= 0, or the streamed bytes do not hash
                to ``artifact_ref``.
        """
        if chunk_size <= 0:
            msg = f"chunk_size must be > 0, got {chunk_size}"
            raise ValueError(msg)

        meta = self.read_meta(artifact_ref)
        self._enforce_read_auth(artifact_ref, meta, auth_context)

        blob_path = self._blob_path(artifact_ref)
        if not blob_path.is_file():
            msg = f"no artifact blob for {artifact_ref.ref}"
            raise FileNotFoundError(msg)

        hasher = hashlib.sha256()
        with blob_path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                yield chunk
        actual = f"sha256:{hasher.hexdigest()}"
        if actual != artifact_ref.ref:
            msg = (
                f"artifact hash mismatch for {artifact_ref.ref}: streamed bytes "
                f"hash to {actual} (on-disk corruption or tampering)"
            )
            raise ValueError(msg)

    def read_blob(self, ref: ModelArtifactRef) -> bytes:
        """Return the blob bytes for ``ref``, hash-verified (no auth gate).

        Retained for the unrestricted internal callers from the minimal slice.
        Restricted-kind reads must go through :meth:`read` with an
        ``auth_context``; this method does not enforce the restricted-tier gate.

        Raises:
            FileNotFoundError: if no blob exists for ``ref``.
            ValueError: if the stored bytes do not hash to ``ref``.
        """
        blob_path = self._blob_path(ref)
        if not blob_path.is_file():
            msg = f"no artifact blob for {ref.ref}"
            raise FileNotFoundError(msg)
        data = blob_path.read_bytes()
        self._verify_hash(ref, data)
        return data

    def read_meta(self, ref: ModelArtifactRef) -> ModelArtifactMetadata:
        """Return the typed sidecar metadata for ``ref``.

        Raises:
            FileNotFoundError: if no sidecar exists for ``ref``.
            ValueError: if the sidecar is not a JSON object or fails validation.
        """
        meta_path = self._meta_path(ref)
        if not meta_path.is_file():
            msg = f"no artifact sidecar for {ref.ref}"
            raise FileNotFoundError(msg)
        raw = meta_path.read_bytes()
        loaded: object = json.loads(raw)
        if not isinstance(loaded, dict):
            msg = f"artifact sidecar for {ref.ref} is not a JSON object"
            raise ValueError(msg)
        return ModelArtifactMetadata.model_validate(loaded)

    def scope_size_bytes(self, scope_ref: str | None) -> int:
        """Total on-disk blob bytes currently attributed to ``scope_ref``.

        ``secret_detected`` sidecars (which have no blob) are excluded.
        """
        total = 0
        for meta_path in self._iter_meta_paths():
            try:
                loaded = json.loads(meta_path.read_bytes())
            except (OSError, json.JSONDecodeError):  # fallback-ok: skip unreadable
                continue
            if not isinstance(loaded, dict):
                continue
            if loaded.get("scope_ref") != scope_ref:
                continue
            if (
                loaded.get("redaction_state")
                == EnumArtifactRedactionState.SECRET_DETECTED.value
            ):
                continue
            size = loaded.get("artifact_size_bytes")
            if isinstance(size, int):
                total += size
        return total

    def _enforce_per_write_quota(self, stored_bytes: bytes) -> None:
        if (
            self._max_artifact_bytes is not None
            and len(stored_bytes) > self._max_artifact_bytes
        ):
            msg = (
                f"artifact size {len(stored_bytes)} exceeds per-write quota "
                f"{self._max_artifact_bytes}"
            )
            raise ArtifactQuotaExceededError(msg)

    def _enforce_scope_quota(self, scope_ref: str | None, incoming: int) -> None:
        if self._max_scope_bytes is None:
            return
        current = self.scope_size_bytes(scope_ref)
        if current + incoming > self._max_scope_bytes:
            msg = (
                f"scope {scope_ref!r} total {current + incoming} would exceed "
                f"per-scope quota {self._max_scope_bytes}"
            )
            raise ArtifactQuotaExceededError(msg)

    def _enforce_read_auth(
        self,
        ref: ModelArtifactRef,
        meta: ModelArtifactMetadata,
        auth_context: ModelArtifactAuthContext | None,
    ) -> None:
        if not meta.restricted:
            return
        if auth_context is None or not auth_context.is_authorized_for(
            meta.artifact_kind
        ):
            principal = auth_context.principal if auth_context is not None else "<none>"
            msg = (
                f"restricted artifact {ref.ref} (kind={meta.artifact_kind}) "
                f"read denied for principal {principal!r}"
            )
            raise ArtifactUnauthorizedError(msg)

    def _record_secret_detected(
        self,
        ref: ModelArtifactRef,
        *,
        media_type: str,
        artifact_kind: str,
        source_system: str,
        scope_ref: str | None,
        correlation_id: str | None,
        retention_class: EnumArtifactRetentionClass,
        retention_ttl_seconds: int | None,
        restricted: bool,
        size_bytes: int,
    ) -> None:
        """Write a secret_detected sidecar with NO accompanying blob."""
        meta_path = self._meta_path(ref)
        if meta_path.exists():
            return
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        effective_ttl = (
            retention_ttl_seconds
            if retention_ttl_seconds is not None
            else retention_class.default_ttl_seconds
        )
        meta = ModelArtifactMetadata(
            artifact_hash=ref.hex_digest,
            artifact_size_bytes=size_bytes,
            artifact_media_type=media_type,
            artifact_kind=artifact_kind,
            source_system=source_system,
            scope_ref=scope_ref,
            correlation_id=correlation_id,
            retention_class=retention_class,
            retention_ttl_seconds=effective_ttl,
            redaction_state=EnumArtifactRedactionState.SECRET_DETECTED,
            redaction_transform=None,
            restricted=restricted,
            token_estimate=0,
            created_at_utc=datetime.now(UTC).isoformat(),
            writer_version=WRITER_VERSION,
        )
        self._atomic_write(meta_path, self._serialize_meta(meta))

    @staticmethod
    def _verify_hash(ref: ModelArtifactRef, data: bytes) -> None:
        actual = ModelArtifactRef.from_bytes(data)
        if actual != ref:
            msg = (
                f"artifact hash mismatch for {ref.ref}: stored bytes hash to "
                f"{actual.ref} (on-disk corruption or tampering)"
            )
            raise ValueError(msg)

    @staticmethod
    def _serialize_meta(meta: ModelArtifactMetadata) -> bytes:
        return meta.model_dump_json(indent=2).encode()

    def _iter_meta_paths(self) -> Iterator[Path]:
        if not self._root.is_dir():
            return
        for shard in self._root.iterdir():
            if not shard.is_dir():
                continue
            for path in shard.iterdir():
                if path.name.endswith(_META_SUFFIX):
                    yield path

    def _blob_path(self, ref: ModelArtifactRef) -> Path:
        hex_digest = ref.hex_digest
        return self._root / hex_digest[:2] / hex_digest

    def _meta_path(self, ref: ModelArtifactRef) -> Path:
        hex_digest = ref.hex_digest
        return self._root / hex_digest[:2] / f"{hex_digest}{_META_SUFFIX}"

    @staticmethod
    def _atomic_write(dest: Path, data: bytes) -> None:
        """Write ``data`` to ``dest`` via temp file + atomic rename."""
        fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            tmp_path.replace(dest)
        except BaseException:
            tmp_path.unlink(missing_ok=True)  # cleanup-resilience-ok: remove temp file
            raise
