# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Minimal replay response object for golden-chain transports."""

from __future__ import annotations


class ReplayResponse:
    """Minimal ``httpx.Response``-shaped object the inference handlers consume."""

    __slots__ = ("_json_body", "status_code")

    def __init__(self, status_code: int, json_body: dict[str, object]) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self) -> dict[str, object]:
        return self._json_body

    def raise_for_status(self) -> None:
        # Recorded responses are 2xx by construction; a recorded error body is a
        # distinct fixture the caller would assert on directly.
        return None


__all__ = ["ReplayResponse"]
