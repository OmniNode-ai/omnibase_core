# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire model of ``onex.evt.platform.validator-triggered.v1`` (OMN-21277)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorTriggeredEvent"]


class ModelValidatorTriggeredEvent(BaseModel):
    """One validator that failed a change (RULING 2026-10-14T20:01:09Z).

    Published once per validator whose canonical ValidationReport carries a
    FAIL or ERROR finding. ``severity`` is the worst of them (ERROR outranks
    FAIL); ``locations`` lists the triggering findings' locations in report
    order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validator_name: str = Field(
        min_length=1,
        description="The report's validator_id, e.g. ci_inheritance_check.",
    )
    severity: Literal["FAIL", "ERROR"]
    finding_count: int = Field(ge=1)
    locations: tuple[str, ...] = Field(default=())
    repository: str = Field(min_length=1)
    pull_request: int | None = Field(default=None, ge=1)
    head_sha: str | None = Field(default=None, min_length=7, max_length=64)
    correlation_id: UUID
