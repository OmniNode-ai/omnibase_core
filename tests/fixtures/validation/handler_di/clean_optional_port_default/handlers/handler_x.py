# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
class HandlerX:
    def __init__(self, container):
        self._container = container

    def handle(self, request, retries: int | None = None):
        return retries
