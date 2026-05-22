# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Utility functions for context pack chunk ID generation."""

from __future__ import annotations

import hashlib


def compute_chunk_id(factor: str, content: str) -> str:
    """Return a deterministic chunk_id for a given factor and content.

    Format: ``ctx_`` + first 8 hex chars of sha256(factor + ":" + content).

    The 8-char prefix is sufficient for v1 intra-pack deduplication.
    The builder is responsible for detecting collisions within a single pack
    and emitting EnumContextPackFailure.ARTIFACT_HASH_MISMATCH if found.
    """
    digest = hashlib.sha256(f"{factor}:{content}".encode()).hexdigest()
    return f"ctx_{digest[:8]}"


__all__ = [
    "compute_chunk_id",
]
