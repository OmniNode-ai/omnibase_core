# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Violations produced by the url-authority scanner."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_url_authority_violation import (
    ModelUrlAuthorityViolation,
)


class ModelUrlAuthorityCheckOutput(BaseModel):
    """Every url-authority violation found across the supplied files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelUrlAuthorityViolation, ...] = ()
