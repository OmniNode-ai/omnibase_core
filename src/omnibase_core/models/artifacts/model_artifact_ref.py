# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact reference (OMN-13091).

``ModelArtifactRef`` is the single reference type for blobs in the
content-addressed artifact store (skill-output durable capture, OMN-13089).
A ref is always ``sha256:<64 lowercase hex chars>`` — the same prefix
convention as ``gate/diff_hash._sha256_prefixed()`` and omnimemory's
``content_blob_ref``.

Unlike the registry-resolved
:class:`~omnibase_core.models.handlers.model_handler_artifact_ref.ModelHandlerArtifactRef`
(an opaque, registry-dependent identifier), this ref IS the content address:
the bytes it points to can be hash-verified against the ref itself.

.. versionadded:: OMN-13091
"""

from __future__ import annotations

import hashlib
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelArtifactRef"]

_SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_PREFIX = "sha256:"


class ModelArtifactRef(BaseModel):
    """Content-addressed reference to a stored artifact.

    The ``ref`` field is the artifact's identity AND its integrity proof:
    ``sha256:<hex>`` where ``<hex>`` is the lowercase SHA-256 digest of the
    artifact bytes. Consumers retrieving the blob re-hash it and compare
    against this ref.

    Example:
        >>> import hashlib
        >>> ref = ModelArtifactRef.from_bytes(b"runtime capture log")
        >>> ref.ref == f"sha256:{hashlib.sha256(b'runtime capture log').hexdigest()}"
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ref: str = Field(
        ...,
        description=(
            "Content-addressed artifact reference in the form "
            "'sha256:<64 lowercase hex chars>'. The hex digest is the "
            "SHA-256 of the artifact bytes."
        ),
    )

    @field_validator("ref")
    @classmethod
    def _validate_sha256_ref(cls, value: str) -> str:
        if not _SHA256_REF_RE.match(value):
            msg = (
                "artifact ref must match 'sha256:<64 lowercase hex chars>', "
                f"got: {value!r}"
            )
            raise ValueError(msg)
        return value

    @property
    def hex_digest(self) -> str:
        """Return the bare 64-char hex digest without the ``sha256:`` prefix."""
        return self.ref.removeprefix(_SHA256_PREFIX)

    @classmethod
    def from_bytes(cls, data: bytes) -> ModelArtifactRef:
        """Compute the content address of ``data`` and return its ref."""
        return cls(ref=f"{_SHA256_PREFIX}{hashlib.sha256(data).hexdigest()}")
