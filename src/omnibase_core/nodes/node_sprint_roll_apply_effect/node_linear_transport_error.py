# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The typed error a sprint-roll Linear transport raises (OMN-20397)."""

from __future__ import annotations

__all__ = ["NodeLinearTransportError"]


class NodeLinearTransportError(RuntimeError):
    """A Linear call failed.

    `status` is the HTTP status when the caller's adapter knows one, and None otherwise.
    It is the only thing this package needs to know about HTTP, and it arrives as data
    rather than as an imported client type.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
