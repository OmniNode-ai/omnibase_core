# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Structural protocol for semantic-version values.

``ProtocolSemVer`` exports the read surface of
``omnibase_core.models.primitives.model_semver.ModelSemVer`` so foundation-layer
TypedDicts and type aliases can annotate version-typed fields WITHOUT importing
the concrete model (a ``types -> models`` import-layering back-edge forbidden by
the ``core-foundation-no-upward`` contract in ``.importlinter``; OMN-3210 /
OMN-14337).

``ModelSemVer`` (a frozen Pydantic model, 345+ importers, imports ``ModelOnexError``)
cannot be relocated down into ``types/`` without an exception-type behavior change
and repo-wide churn, so a structural protocol is used instead. ``ModelSemVer``
satisfies this protocol structurally — no runtime coupling, no behavior change.

Construction of ``ModelSemVer`` instances still happens against the concrete
model imported directly by producing code; this protocol only types the *value*
carried through foundation shapes.
"""

from __future__ import annotations

from typing import Protocol


class SemVerProtocol(Protocol):
    """Structural read surface of a semantic-version value (see ``ModelSemVer``)."""

    @property
    def major(self) -> int:
        pass

    @property
    def minor(self) -> int:
        pass

    @property
    def patch(self) -> int:
        pass

    @property
    def prerelease(self) -> tuple[str | int, ...] | None:
        pass

    @property
    def build(self) -> tuple[str, ...] | None:
        pass

    def to_string(self) -> str:
        pass

    def is_prerelease(self) -> bool:
        pass


ProtocolSemVer = SemVerProtocol

__all__ = ["ProtocolSemVer"]
