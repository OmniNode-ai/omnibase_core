# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Planted: a handler that no node contract sits above reads a file."""

from pathlib import Path


class HandlerX:
    def handle(self, request: Path) -> str:
        text = request.read_text(encoding="utf-8")
        return text
