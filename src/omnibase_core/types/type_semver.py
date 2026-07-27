# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Structural protocol for semantic-version values.

``ProtocolSemVer`` is the SINGLE canonical structural protocol for semantic-version
values across ``omnibase_core`` (OMN-14624). It exports the read surface of
``omnibase_core.models.primitives.model_semver.ModelSemVer`` so foundation-layer
TypedDicts and type aliases can annotate version-typed fields WITHOUT importing
the concrete model (a ``types -> models`` import-layering back-edge forbidden by
the ``core-foundation-no-upward`` contract in ``.importlinter``; OMN-3210 /
OMN-14337).

``omnibase_core.protocols.base.protocol_sem_ver`` re-exports this object so the
historical protocol-layer import path resolves to the *same* canonical protocol.

``ModelSemVer`` (a frozen Pydantic model, 345+ importers, imports ``ModelOnexError``)
cannot be relocated down into ``types/`` without an exception-type behavior change
and repo-wide churn, so a structural protocol is used instead. ``ModelSemVer``
satisfies this protocol structurally — no runtime coupling, no behavior change.

The protocol is ``@runtime_checkable`` so ``isinstance(value, ProtocolSemVer)``
duck-typing checks work (preserving the behavior the former protocol-layer
duplicate offered). This module MUST stay a pure typing-only leaf — it imports
only ``typing`` — so ``types/`` remains importable before ``protocols`` in any
order.

Construction of ``ModelSemVer`` instances still happens against the concrete
model imported directly by producing code; this protocol only types the *value*
carried through foundation shapes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSemVer(Protocol):
    """Structural read surface of a semantic-version value (see ``ModelSemVer``)."""

    @property
    def major(self) -> int: ...

    @property
    def minor(self) -> int: ...

    @property
    def patch(self) -> int: ...

    @property
    def prerelease(self) -> tuple[str | int, ...] | None: ...

    @property
    def build(self) -> tuple[str, ...] | None: ...

    def to_string(self) -> str: ...

    def is_prerelease(self) -> bool: ...

    def __str__(self) -> str: ...


__all__ = ["ProtocolSemVer"]
