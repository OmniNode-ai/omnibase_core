# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTaskDeltaEnvelope — incremental task state change for overseer projection (OMN-10251)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(
    reason=(
        "task_id and runner_id are overseer wire IDs (correlation strings), "
        "not system UUIDs."
    )
)
@allow_dict_str_any(
    reason="payload is a heterogeneous incremental task delta with varying value types."
)
class ModelTaskDeltaEnvelope(BaseModel, frozen=True, extra="forbid"):
    """Incremental task state change for overseer projection.

    Carries only the fields that changed, plus the mandatory task_id.
    """

    task_id: str  # string-id-ok: overseer correlation string
    status: EnumTaskStatus | None = None
    runner_id: str | None = None  # string-id-ok: overseer runner correlation string
    attempt: int | None = Field(default=None, ge=1)
    payload: Mapping[str, Any] | None = (
        None  # ONEX_EXCLUDE: dict_str_any - incremental task delta
    )
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # string-version-ok: wire type across overseer/runner boundary; JSON
    schema_version: str = "1.0"

    @field_validator("payload", mode="before")
    @classmethod
    def _freeze_payload(
        cls, value: Mapping[str, Any] | None
    ) -> Mapping[str, Any] | None:
        if value is None:
            return None
        return MappingProxyType(dict(value))


__all__ = ["ModelTaskDeltaEnvelope"]
