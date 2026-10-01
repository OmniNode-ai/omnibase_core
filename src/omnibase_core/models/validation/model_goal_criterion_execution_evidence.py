# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)


class ModelGoalCriterionExecutionEvidence(BaseModel):
    """One criterion's observed outcome in the immutable execution result R."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str = Field(
        ..., min_length=1, max_length=128
    )  # string-id-ok: contract criterion key
    outcome: Literal["passed", "failed", "not_run"]
    evidence_sha256: str

    @field_validator("evidence_sha256")
    @classmethod
    def _evidence_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("evidence digest must use sha256:<64 lowercase hex>")
        return value
