# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clean: public methods only read; lifecycle setup is the declared exemption."""


class ModelRecordRequest:
    pass


class HandlerRecording:
    def __init__(self) -> None:
        self._items: list[str] = []

    def initialize(self) -> None:
        self._items = []

    def handle(self, request: ModelRecordRequest) -> int:
        return len(self._items)

    def count(self, prefix: str) -> int:
        return len([i for i in self._items if i.startswith(prefix)])
