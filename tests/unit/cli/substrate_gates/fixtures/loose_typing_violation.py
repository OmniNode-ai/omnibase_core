# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: loose typing violations — all forms the gate must detect."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel


class ModelWithDictAny(BaseModel):
    context: dict[str, Any]


class ModelWithAny(BaseModel):
    payload: Any


class ModelWithMappingAny(BaseModel):
    extra: Mapping[str, Any]


class ProtocolWithAnyArg(Protocol):
    def handle(self, arg: Any) -> None: ...


class ProtocolWithDictAnyArg(Protocol):
    def process(self, data: dict[str, Any]) -> None: ...


class ProtocolWithKwargsAny(Protocol):
    def run(self, **kwargs: Any) -> None: ...


class ProtocolWithKwargsObject(Protocol):
    def execute(self, **kwargs: object) -> None: ...
