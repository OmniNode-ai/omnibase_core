# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: Protocol methods with banned *args/kwargs annotations — should be flagged."""

from __future__ import annotations

from typing import Any, Protocol


class ViolationKwargsObject(Protocol):
    def execute(self, **kwargs: object) -> None:
        raise NotImplementedError


class ViolationKwargsAny(Protocol):
    def run(self, **kwargs: Any) -> None:
        raise NotImplementedError


class ViolationArgsObject(Protocol):
    def call(self, *args: object) -> None:
        raise NotImplementedError


class ViolationArgsAny(Protocol):
    def invoke(self, *args: Any) -> None:
        raise NotImplementedError


class ViolationBothAny(Protocol):
    def dispatch(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class ViolationBothObject(Protocol):
    def process(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError
