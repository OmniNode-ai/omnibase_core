# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance result model for a single node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_scan.model_check_result import (
    ModelCheckResult,
)

__all__ = ["ModelScanCheckResult"]


class ModelScanCheckResult(BaseModel):
    """Compliance result for a single node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str
    contract_path: str
    passed: bool
    checks: list[ModelCheckResult] = Field(default_factory=list)
