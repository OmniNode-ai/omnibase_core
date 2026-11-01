# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Planted: a public method other than handle that mutates a registry through callables it was handed."""

from collections.abc import Callable


class ModelRecordRequest:
    pass


class HandlerRegistering:
    def handle(self, request: ModelRecordRequest) -> int:
        return 0

    def register(
        self,
        registry_calls: tuple[Callable[[str], bool], Callable[[str, object], object]],
        key: str,
        instance: object,
    ) -> None:
        unregister, register_instance = registry_calls
        unregister(key)
        register_instance(key, instance)
