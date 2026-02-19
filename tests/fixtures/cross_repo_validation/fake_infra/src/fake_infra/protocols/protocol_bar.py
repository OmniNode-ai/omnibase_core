# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Public protocol - allowed for cross-repo import."""

from __future__ import annotations

from typing import Protocol


class ProtocolBar(Protocol):
    """Sample infra protocol."""

    def process(self, data: str) -> bool:
        """Process data and return success."""
        ...
