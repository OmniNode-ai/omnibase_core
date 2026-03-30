# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unified state store protocol for node state persistence.

Semantics (behavioral contract):
- Namespace: keyed by (node_id, scope_id) where scope_id defaults to "default"
- Read-after-write: get() after put() within same process returns written value
- Overwrite: put() replaces entire state snapshot (not patch-based)
- Missing state: get() on nonexistent key returns None, not error
- Metadata: every persisted state carries written_at and contract_fingerprint
- Versioning: state format changes require contract version bump
- Delete: delete() on missing state returns False (not error). Successful delete returns True.
- Key listing: list_keys() returns sorted list of (node_id, scope_id) tuples. Sorted by
  node_id then scope_id. Stable ordering is required for deterministic tests.
- Fingerprint: contract_fingerprint defaults to "" for backwards compat but authoritative
  writes (from verified workflows) SHOULD provide a non-empty fingerprint.
- Corruption: implementations must distinguish missing state (returns None) from
  corrupt/unreadable state (raises StateCorruptionError). Corruption must NOT silently
  collapse to None.

.. versionadded:: 0.35.1
    Added as part of Local-First Node Runtime (OMN-7061)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ProtocolStateStore"]


class StateCorruptionError(Exception):
    """Raised when persisted state is corrupt or unreadable.

    Distinct from missing state (which returns None). Implementations must raise
    this when data exists but cannot be deserialized or fails integrity checks.
    """


class ModelStateEnvelope(BaseModel):
    """Wrapper for persisted state with metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str
    scope_id: str = Field(default="default")
    # ONEX_EXCLUDE: dict_str_any — generic state payload, schema enforced by caller
    data: dict[str, Any]
    written_at: datetime
    contract_fingerprint: str = Field(default="")


@runtime_checkable
class ProtocolStateStore(Protocol):
    """Unified protocol for node state persistence."""

    async def get(
        self, node_id: str, scope_id: str = "default"
    ) -> ModelStateEnvelope | None: ...

    async def put(self, envelope: ModelStateEnvelope) -> None: ...

    async def delete(self, node_id: str, scope_id: str = "default") -> bool: ...

    async def exists(self, node_id: str, scope_id: str = "default") -> bool: ...

    async def list_keys(self, node_id: str | None = None) -> list[tuple[str, str]]: ...
