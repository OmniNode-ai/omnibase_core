# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: Protocol methods with banned *args/kwargs annotations — should be flagged."""

from __future__ import annotations

from typing import Any, Protocol


class ViolationKwargsObject(Protocol):
    def execute(self, **kwargs: object) -> None: ...


class ViolationKwargsAny(Protocol):
    def run(self, **kwargs: Any) -> None: ...


class ViolationArgsObject(Protocol):
    def call(self, *args: object) -> None: ...


class ViolationArgsAny(Protocol):
    def invoke(self, *args: Any) -> None: ...


class ViolationBothAny(Protocol):
    def dispatch(self, *args: Any, **kwargs: Any) -> None: ...


class ViolationBothObject(Protocol):
    def process(self, *args: object, **kwargs: object) -> None: ...
