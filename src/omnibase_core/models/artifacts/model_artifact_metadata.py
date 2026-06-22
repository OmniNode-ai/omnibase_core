# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Artifact metadata sidecar model (OMN-13152).

``ModelArtifactMetadata`` is the typed representation of the JSON sidecar
(``<hex>.meta.json``) written next to every blob in the durable-capture
:class:`~omnibase_core.artifacts.artifact_store.ArtifactStore`. It finalizes
the Phase 1 sidecar fields: retention class + TTL, redaction state + applied
transform, and visibility tier.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.artifacts.enum_artifact_redaction_state import (
    EnumArtifactRedactionState,
)
from omnibase_core.enums.artifacts.enum_artifact_retention_class import (
    EnumArtifactRetentionClass,
)

__all__ = ["ModelArtifactMetadata"]


class ModelArtifactMetadata(BaseModel):
    """Typed metadata sidecar for a stored artifact.

    Persisted as the ``<hex>.meta.json`` sidecar. The model is the source of
    truth for the sidecar shape; :class:`ArtifactStore` serializes it on write
    and validates it on read. ``extra="forbid"`` so an unexpected on-disk field
    fails loudly rather than being silently dropped.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    artifact_hash: str = Field(
        ...,
        description="Bare 64-char lowercase SHA-256 hex digest of the stored bytes.",
    )
    artifact_size_bytes: int = Field(
        ...,
        ge=0,
        description="Size of the stored bytes in bytes.",
    )
    artifact_media_type: str = Field(
        ...,
        min_length=1,
        description="IANA media type of the artifact content.",
    )
    artifact_kind: str = Field(
        ...,
        min_length=1,
        description="Logical kind of the artifact (e.g. tool_stdout, session_transcript).",
    )
    source_system: str = Field(
        ...,
        min_length=1,
        description="System that produced the artifact (e.g. local_cli, onex_node).",
    )
    scope_ref: str | None = Field(
        default=None,
        description="Optional scope the artifact belongs to (e.g. ticket/repo ref).",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional correlation id linking the artifact to a workflow.",
    )

    retention_class: EnumArtifactRetentionClass = Field(
        ...,
        description="Retention class governing eviction eligibility.",
    )
    retention_ttl_seconds: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Effective TTL in seconds; None means no expiry (permanent class)."
        ),
    )

    redaction_state: EnumArtifactRedactionState = Field(
        ...,
        description="Redaction state of the stored bytes.",
    )
    redaction_transform: str | None = Field(
        default=None,
        description=(
            "Identifier of the redaction transform applied, if any. Set when "
            "redaction_state is 'redacted'."
        ),
    )

    restricted: bool = Field(
        default=False,
        description=(
            "Whether reads require authorization (restricted visibility tier)."
        ),
    )

    token_estimate: int = Field(
        ...,
        ge=0,
        description="Crude byte-based token estimate for budget previews.",
    )
    created_at_utc: str = Field(
        ...,
        description="ISO-8601 UTC timestamp of creation.",
    )
    writer_version: str = Field(
        ...,
        min_length=1,
        description="Sidecar generation marker of the writer that produced it.",
    )
