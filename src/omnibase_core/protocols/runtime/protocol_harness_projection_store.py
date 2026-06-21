# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ProtocolHarnessProjectionStore: projection-store seam for the local runtime harness (OMN-13420)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.runtime.harness.model_projection_row import (
        ModelProjectionRow,
    )


@runtime_checkable
class ProtocolHarnessProjectionStore(Protocol):
    """Minimal projection-store shape used by the harness REDUCER handler.

    The default implementation is SQLite (zero infra, zero LAN); a Postgres
    implementation is reserved for real migration/view validation.
    """

    @property
    def backend(self) -> str:
        """Return a human-readable backend identifier for evidence packets."""
        raise NotImplementedError  # stub-ok: protocol declaration only

    def write(self, row: ModelProjectionRow) -> None:
        """Persist a single projection row."""
        raise NotImplementedError  # stub-ok: protocol declaration only

    def read(self, correlation_id: UUID) -> ModelProjectionRow | None:
        """Read back the projection row for a correlation ID, or None."""
        raise NotImplementedError  # stub-ok: protocol declaration only


__all__ = ["ProtocolHarnessProjectionStore"]
