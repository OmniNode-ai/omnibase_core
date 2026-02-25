# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical hash utility for content-addressed storage.

Provides a single, authoritative implementation of canonical hashing used
throughout the overlay resolution system: merge engine hashing, pack
manifest hashing, and verifier hashing all call this module.

RFC 8785 compatible: keys are sorted, output is ASCII-encoded.

.. versionadded:: OMN-2754
"""

import hashlib
import json
from typing import Any

__all__ = ["compute_canonical_hash"]


def _strip_none_values(obj: Any) -> Any:
    """Recursively remove None-valued keys from dicts.

    Absent fields and None fields are semantically equivalent for hashing
    purposes: the canonical form omits both. This ensures that a model
    serialized with ``exclude_none=True`` produces the same hash as one
    serialized with explicit ``None`` values.

    Args:
        obj: Any JSON-serialisable value.

    Returns:
        The input with all ``None`` dictionary values removed (recursively).
        Non-dict/list values are returned unchanged.
    """
    if isinstance(obj, dict):
        return {k: _strip_none_values(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none_values(item) for item in obj]
    return obj


def compute_canonical_hash(obj: object) -> str:
    """Return the SHA-256 hex digest of the canonical JSON representation.

    Rules:
    - ``json.dumps`` with ``sort_keys=True``, ``ensure_ascii=True`` (RFC 8785 compatible).
    - ``None`` fields are stripped before hashing — absent == None.
    - Empty lists (``[]``) are NOT stripped; they are distinct from ``None``.
      (ModelContractPatch already normalises ``[]`` → ``None`` for list-ops.)

    This is the single source of truth for all content hashing in the overlay
    system. Any component that needs to hash a contract, patch, or manifest must
    call this function rather than rolling its own serialisation logic.

    Args:
        obj: Any object that can be converted to a JSON-serialisable dict via
            ``model_dump()`` (Pydantic) or is already JSON-serialisable.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).

    Example:
        >>> from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
        >>> compute_canonical_hash({"b": 2, "a": 1, "c": None})
        '...'  # deterministic, None key stripped, keys sorted
        >>> compute_canonical_hash({"a": 1, "b": 2})  # same after stripping
        '...'
    """
    # Pydantic models expose model_dump(); fall back to __dict__ then identity.
    if hasattr(obj, "model_dump"):
        raw: Any = obj.model_dump()
    elif isinstance(obj, dict):
        raw = obj
    else:
        # Fallback: attempt direct serialisation (e.g. for simple scalars).
        raw = obj

    stripped = _strip_none_values(raw)
    canonical_json = json.dumps(stripped, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("ascii")).hexdigest()
