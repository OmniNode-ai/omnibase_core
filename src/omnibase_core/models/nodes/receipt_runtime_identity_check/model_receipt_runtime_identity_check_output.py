# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Violations and receipt count produced by the runtime-identity gate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_runtime_identity_violation import (
    ModelRuntimeIdentityViolation,
)


class ModelReceiptRuntimeIdentityCheckOutput(BaseModel):
    """Runtime-identity violations, plus how many scanned files were receipts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelRuntimeIdentityViolation, ...] = ()
    receipts_found: int = 0
