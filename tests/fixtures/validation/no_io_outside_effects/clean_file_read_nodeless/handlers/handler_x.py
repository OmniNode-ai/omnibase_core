# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Clean: a handler that no node contract sits above takes the text in its request."""


class HandlerX:
    def handle(self, request: str) -> str:
        return request.strip()
