# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Planted: a public method other than handle that mutates handler state."""


class ModelRecordRequest:
    pass


class HandlerRecording:
    def __init__(self) -> None:
        self._items: list[str] = []

    def handle(self, request: ModelRecordRequest) -> int:
        return len(self._items)

    def record(self, item: str) -> None:
        self._items.append(item)
