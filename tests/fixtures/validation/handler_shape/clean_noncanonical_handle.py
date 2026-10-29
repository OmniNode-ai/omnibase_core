# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clean: a handler class whose handle takes one typed request."""


class ModelProbeRequest:
    pass


class HandlerProbe:
    def handle(self, request: ModelProbeRequest) -> None:
        return None
