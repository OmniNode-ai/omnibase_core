# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clean: a handler module whose behaviour is a handler class; helpers stay private."""


class ModelGatherRequest:
    pass


def _roots(root: str) -> list[str]:
    return [root]


class HandlerGather:
    def handle(self, request: ModelGatherRequest) -> list[str]:
        return _roots("x")
