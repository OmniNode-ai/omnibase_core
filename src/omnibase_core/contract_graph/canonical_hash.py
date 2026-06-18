# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonicalization + stable hashing for Contract Graph IR import.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

The IR embeds two stable hashes so diff evidence cannot drift between runs:

1. ``canonical_contract_sha256`` — sha256 over the *canonicalized* contract
   bytes (recursively key-sorted, ``_metadata`` excluded so build-time noise
   never perturbs the hash). This is the per-source-contract hash.
2. ``adapter_version_sha256`` — a stable hash of an adapter's identity + the
   source bytes of the function objects that implement it, so a behavioral
   change to an adapter changes its version hash deterministically.

Both are pure functions of their inputs — no clock, no environment, no I/O.
"""

from __future__ import annotations

import hashlib
import json

from omnibase_core.types.type_json import JsonType

__all__ = [
    "canonicalize_contract",
    "canonical_contract_sha256",
    "adapter_version_sha256",
]

# Build-time / non-semantic keys excluded from canonicalization so the per-source
# hash reflects only the functional contract (matches cli_contract_diff's
# DEFAULT_EXCLUDE_PREFIXES intent of dropping the _metadata section).
_CANONICAL_EXCLUDE_KEYS: frozenset[str] = frozenset({"_metadata"})


def canonicalize_contract(data: dict[str, JsonType]) -> dict[str, JsonType]:
    """Return a canonical, semantics-only view of a contract dict.

    Recursively drops excluded top-level build-time keys. Ordering is not
    applied to the dict structure itself (JSON serialization with
    ``sort_keys=True`` handles deterministic ordering at hash time), but excluded
    keys are removed so byte-noise in ``_metadata`` never perturbs the hash.
    """
    return {
        key: value for key, value in data.items() if key not in _CANONICAL_EXCLUDE_KEYS
    }


def canonical_contract_sha256(data: dict[str, JsonType]) -> str:
    """sha256 over the canonicalized contract bytes, as ``"sha256:<hex>"``.

    The dict is canonicalized (excluded keys dropped) then serialized with
    sorted keys and compact separators so the byte representation is
    deterministic regardless of source key order or whitespace.
    """
    canonical = canonicalize_contract(data)
    payload = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def adapter_version_sha256(
    adapter_name: str,
    implementation_sources: tuple[str, ...],
) -> str:
    """Stable version hash for a dialect adapter, as ``"sha256:<hex>"``.

    Combines the adapter's declared name with the source bytes of the functions
    that implement it (callers pass ``inspect.getsource(fn)`` for each). A
    behavioral change to any implementing function changes its source and
    therefore the version hash, so the IR's embedded ``adapter_version_sha256``
    deterministically tracks adapter changes. Pure: no Any, no I/O of its own.
    """
    parts: list[str] = [f"adapter:{adapter_name}", *implementation_sources]
    payload = "\n".join(parts).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
