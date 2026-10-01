# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationRevision."""

from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)


class ModelGoalMutationRevision(BaseModel):
    """One authenticated contract revision participating in a mutation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: UUID
    contract_sha256: str

    @field_validator("contract_sha256")
    @classmethod
    def _contract_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("contract digest must use sha256:<64 lowercase hex>")
        return value
