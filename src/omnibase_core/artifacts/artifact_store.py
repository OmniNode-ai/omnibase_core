# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# parent-plan: Phase 1 extends this — this is the MINIMAL slice of the
# durable-capture artifact store (docs/plans/
# 2026-06-12-durable-capture-ingestion-intelligence-plan.md, Phase 1),
# built for the skill-output suppression slice (OMN-13089 / OMN-13093).
# Explicitly deferred to parent Phase 1 (extend in place, same module):
# retention/quota policy, redaction transforms, restricted-topic handling,
# authorized read API. Do NOT mistake this for the finished store.

"""Minimal content-addressed artifact store (OMN-13093).

Blobs are stored under ``$ONEX_ARTIFACT_STORE_ROOT`` at the sharded path
``<root>/<hh>/<full-hex>`` where ``<hh>`` is the first two hex chars of the
blob's SHA-256 digest. Every blob carries a JSON metadata sidecar
``<full-hex>.meta.json`` with the ``artifact-captured`` required fields.

Design constraints (ticket spec):

- stdlib + Pydantic only — no infra deps — so omniclaude hooks import this
  module cleanly (layering rule 7 / F14)
- store root from ``os.environ["ONEX_ARTIFACT_STORE_ROOT"]`` — required env,
  ``KeyError`` on absence (fail-fast, Operating Rule 8); callers set it from
  ``$OMNI_HOME/.onex_state/artifacts/``
- atomic temp+rename writes, idempotent on existing hash
- reads are hash-verified against the content address

.. versionadded:: OMN-13093
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

__all__ = [
    "ARTIFACT_STORE_ROOT_ENV",
    "WRITER_VERSION",
    "ArtifactStore",
]

ARTIFACT_STORE_ROOT_ENV = "ONEX_ARTIFACT_STORE_ROOT"

# Sidecar generation marker. Parent Phase 1 extensions (retention, redaction,
# read-API hardening) bump this so they can distinguish sidecar generations.
WRITER_VERSION = "omn-13093-minimal-1"

# Crude byte-based token estimate (~4 bytes/token for English-ish text).
# Good enough for projection previews and budget heuristics; NOT a tokenizer.
_BYTES_PER_TOKEN_ESTIMATE = 4

_META_SUFFIX = ".meta.json"


class ArtifactStore:
    """Content-addressed blob store with JSON metadata sidecars.

    The blob's :class:`ModelArtifactRef` (``sha256:<hex>``) is both its
    identity and its integrity proof: :meth:`read_blob` re-hashes the bytes
    on retrieval and fails on mismatch.
    """

    def __init__(self) -> None:
        # Fail-fast: KeyError when ONEX_ARTIFACT_STORE_ROOT is unset.
        # No silent default — a wrong default is worse than a loud crash.
        self._root = Path(os.environ[ARTIFACT_STORE_ROOT_ENV])

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
    ) -> ModelArtifactRef:
        """Store ``data`` content-addressed and return its ref.

        Writes are atomic (temp file + ``os.replace`` in the destination
        directory) and idempotent: if a blob with the same hash already
        exists, neither the blob nor its sidecar is rewritten (first writer
        wins for metadata).
        """
        ref = ModelArtifactRef.from_bytes(data)
        blob_path = self._blob_path(ref)
        if blob_path.exists():
            return ref

        shard_dir = blob_path.parent
        shard_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "artifact_hash": ref.hex_digest,
            "artifact_size_bytes": len(data),
            "artifact_media_type": media_type,
            "artifact_kind": artifact_kind,
            "source_system": source_system,
            "scope_ref": scope_ref,
            "correlation_id": correlation_id,
            # Minimal slice always stores raw bytes; redaction transforms are
            # a parent Phase 1 extension.
            "redaction_state": "raw",
            "token_estimate": len(data) // _BYTES_PER_TOKEN_ESTIMATE,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "writer_version": WRITER_VERSION,
        }

        # Sidecar first, blob last: blob presence is the idempotency signal,
        # so a crash between the two writes never yields a blob without meta.
        self._atomic_write(self._meta_path(ref), json.dumps(meta, indent=2).encode())
        self._atomic_write(blob_path, data)
        return ref

    def read_blob(self, ref: ModelArtifactRef) -> bytes:
        """Return the blob bytes for ``ref``, hash-verified.

        Raises:
            FileNotFoundError: if no blob exists for ``ref``.
            ValueError: if the stored bytes do not hash to ``ref``
                (on-disk corruption or tampering).
        """
        data = self._blob_path(ref).read_bytes()
        actual = ModelArtifactRef.from_bytes(data)
        if actual != ref:
            msg = (
                f"artifact hash mismatch for {ref.ref}: stored bytes hash to "
                f"{actual.ref} (on-disk corruption or tampering)"
            )
            raise ValueError(msg)
        return data

    def read_meta(self, ref: ModelArtifactRef) -> dict[str, object]:
        """Return the JSON sidecar metadata for ``ref``.

        Raises:
            FileNotFoundError: if no sidecar exists for ``ref``.
            ValueError: if the sidecar does not contain a JSON object.
        """
        raw = self._meta_path(ref).read_bytes()
        meta: object = json.loads(raw)
        if not isinstance(meta, dict):
            msg = f"artifact sidecar for {ref.ref} is not a JSON object"
            raise ValueError(msg)
        return meta

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
