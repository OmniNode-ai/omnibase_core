# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationContextReadback."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)


class ModelGoalMutationContextReadback(BaseModel):
    """Exact verified App response after blocking one issued check context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: UUID
    app_integration_id: str = Field(  # string-id-ok: GitHub App installation identifier
        ..., min_length=1, max_length=128
    )
    check_run_id: str = Field(  # string-id-ok: GitHub Check Run identifier
        ..., min_length=1, max_length=128
    )
    external_id: str = Field(..., min_length=1, max_length=256)
    context_name: str = Field(..., min_length=1, max_length=256)
    head_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    status: Literal["completed"]
    conclusion: Literal["failure", "cancelled", "timed_out", "action_required"]
    title: str = Field(..., min_length=1, max_length=256)
    summary: str = Field(..., min_length=1, max_length=65535)
    remote_readback_sha256: str
    read_at: datetime

    @field_validator("remote_readback_sha256")
    @classmethod
    def _readback_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("readback digest must use sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def _read_time_is_aware(self) -> Self:
        if self.read_at.tzinfo is None or self.read_at.utcoffset() is None:
            raise ValueError("read_at must include a timezone")
        payload = {
            "app_integration_id": self.app_integration_id,
            "check_run_id": self.check_run_id,
            "conclusion": self.conclusion,
            "context_name": self.context_name,
            "external_id": self.external_id,
            "head_sha": self.head_sha,
            "status": self.status,
            "summary": self.summary,
            "title": self.title,
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        expected_digest = (
            f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        )
        if expected_digest != self.remote_readback_sha256:
            raise ValueError("App remote readback digest does not match its fields")
        return self
