# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationContext."""

from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)


class ModelGoalMutationContext(BaseModel):
    """One previously issued App check context affected by a goal mutation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    app_integration_id: str = Field(  # string-id-ok: GitHub App installation identifier
        ..., min_length=1, max_length=128
    )
    context_name: str = Field(..., min_length=1, max_length=256)
    head_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    contract_revision: UUID
    attempt_id: UUID
    attempt_sequence: int = Field(..., ge=1)
    check_run_id: str = Field(  # string-id-ok: GitHub Check Run identifier
        ..., min_length=1, max_length=128
    )
    external_id: str = Field(..., min_length=1, max_length=256)
    request_sha256: str

    @field_validator("request_sha256")
    @classmethod
    def _request_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("request digest must use sha256:<64 lowercase hex>")
        return value
