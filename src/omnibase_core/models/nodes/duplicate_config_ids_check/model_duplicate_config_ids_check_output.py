# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Violations produced by the duplicate-config-ids validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_duplicate_id_violation import (
    ModelDuplicateIdViolation,
)


class ModelDuplicateConfigIdsCheckOutput(BaseModel):
    """Every duplicate-id violation found across the manifest's registries."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelDuplicateIdViolation, ...] = ()
