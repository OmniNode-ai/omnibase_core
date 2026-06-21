# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Protocol for local runtime bus messages."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLocalRuntimeMessage(Protocol):
    """Minimal bus message shape consumed by the local runtime."""

    value: object


__all__: list[str] = ["ProtocolLocalRuntimeMessage"]
