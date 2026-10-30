# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clean: a handler core that takes the typed payload model."""


class ModelPayload:
    pass


class HandlerPayload:
    def handle(self, request: ModelPayload) -> None:
        return None
