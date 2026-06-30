# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Protocol for local runtime result dump models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLocalRuntimeDumpModel(Protocol):
    """Model shape used for persisting handler return values."""

    def model_dump(self, *, mode: str) -> object:
        """Dump the model into a JSON-compatible object."""
        raise NotImplementedError


__all__: list[str] = ["ProtocolLocalRuntimeDumpModel"]
