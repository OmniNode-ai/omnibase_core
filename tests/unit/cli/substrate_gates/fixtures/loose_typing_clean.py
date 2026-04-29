# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: clean typing — no violations the gate should detect."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel


class ModelClean(BaseModel):
    context: dict[str, str]
    payload: str
    count: int
    identifier: UUID


class ModelWithAllowAnnotation(BaseModel):
    raw_context: dict[str, Any]  # substrate-allow: yaml-deserialization-boundary


class ModelWithOnexExclude(BaseModel):
    legacy_field: Any  # ONEX_EXCLUDE: any_type


class ModelWithAiSlopOk(BaseModel):
    passthrough: dict[str, Any]  # ai-slop-ok


class ProtocolClean(Protocol):
    def handle(self, request: str) -> None:
        raise NotImplementedError

    def process(self, data: dict[str, str]) -> None:
        raise NotImplementedError
