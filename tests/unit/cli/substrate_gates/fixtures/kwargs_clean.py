# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: clean Protocol methods — should NOT be flagged."""

from __future__ import annotations

from typing import Any, Protocol


class CleanExplicitParams(Protocol):
    def execute(self, name: str, value: int) -> None: ...


class CleanNoVarargs(Protocol):
    def run(self, x: int, y: str) -> None: ...


class CleanAllowAnnotated(Protocol):
    def call(self, **kwargs: object) -> None: ...  # substrate-allow: vestigial-protocol


class CleanNonProtocol:
    def execute(self, **kwargs: object) -> None: ...


class CleanNonProtocolAny:
    def run(self, *args: Any, **kwargs: Any) -> None: ...


class CleanTypedKwargs(Protocol):
    def dispatch(self, **kwargs: str) -> None: ...
