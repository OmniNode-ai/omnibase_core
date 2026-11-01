# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clean: public methods read through the callables they are handed and return the new value."""

from collections.abc import Callable


class ModelRecordRequest:
    pass


class HandlerRegistering:
    def handle(self, request: ModelRecordRequest) -> int:
        return 0

    def lookup(
        self,
        read_calls: tuple[Callable[[str], object], Callable[[str], bool]],
        key: str,
    ) -> object | None:
        get_instance, has_instance = read_calls
        return get_instance(key) if has_instance(key) else None

    def plan(self, resolve: Callable[[str], str], key: str) -> str:
        return resolve(key)
