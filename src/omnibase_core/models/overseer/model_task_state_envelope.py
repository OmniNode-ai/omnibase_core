# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTaskStateEnvelope — full task state snapshot for overseer projection (OMN-10251)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(
    reason=(
        "task_id and runner_id are overseer wire IDs (correlation strings), "
        "not system UUIDs. Overseer state machine uses string-keyed tasks."
    )
)
@allow_dict_str_any(
    reason=(
        "payload is a heterogeneous task state payload with varying value types per domain."
    )
)
class ModelTaskStateEnvelope(BaseModel, frozen=True, extra="forbid"):
    """Full task state snapshot for overseer projection."""

    task_id: str = Field(  # string-id-ok: overseer correlation string
        ..., description="Task identifier from upstream task record."
    )
    status: EnumTaskStatus
    domain: str
    node_id: str
    runner_id: str | None = None  # string-id-ok: overseer runner correlation string
    attempt: int = Field(default=1, ge=1)
    payload: Mapping[str, Any] = Field(
        default_factory=lambda: MappingProxyType({})
    )  # ONEX_EXCLUDE: dict_str_any - heterogeneous task state
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # string-version-ok: wire type across overseer/runner boundary; JSON
    schema_version: str = "1.0"

    @field_validator("payload", mode="before")
    @classmethod
    def _freeze_payload(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            return MappingProxyType(dict(value))
        except TypeError as exc:
            raise ValueError("payload must be a mapping") from exc

    @model_validator(mode="after")
    def _freeze_payload_after_validation(self) -> Self:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        return self


__all__ = ["ModelTaskStateEnvelope"]
