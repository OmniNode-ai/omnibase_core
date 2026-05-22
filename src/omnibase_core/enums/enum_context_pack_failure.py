# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context pack failure enum for context pack builder node."""

from __future__ import annotations

from enum import Enum


class EnumContextPackFailure(str, Enum):
    """Failure classification for context pack builder errors."""

    REQUIRED_FACTOR_MISSING = "required_factor_missing"
    PROFILE_NOT_FOUND = "profile_not_found"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    INVALID_PROFILE = "invalid_profile"
    # 8-char sha256 prefix has non-zero collision probability across large chunk sets;
    # builder must detect collisions and emit this failure rather than silently
    # duplicate chunk_ids within a single pack.
    ARTIFACT_HASH_MISMATCH = "artifact_hash_mismatch"


__all__ = [
    "EnumContextPackFailure",
]
