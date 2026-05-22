# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context pack model for context pack pipeline (OMN-11678)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.pack.model_context_chunk import ModelContextChunk


class ModelContextPack(BaseModel):
    """An immutable, versioned context pack delivered to a model for generation.

    generated_at must be a timezone-aware ISO8601 UTC string.
    chunks is a tuple of ModelContextChunk, preserving factor precedence order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pack_id: str  # string-id-ok: opaque content-addressed pack identifier, not a UUID
    contract_hash: str
    model_id: str  # string-id-ok: LLM model name string (e.g. "glm-4-5"), not a UUID
    chunks: tuple[ModelContextChunk, ...]
    total_token_estimate: int
    generated_at: str  # ISO8601 UTC, timezone-aware
    # string-version-ok: profile version label, may be semver or content hash
    profile_version: str


__all__ = [
    "ModelContextPack",
]
