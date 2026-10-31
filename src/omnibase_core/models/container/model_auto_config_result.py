# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of discovering and registering container backends."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.container.model_backend_finding import ModelBackendFinding


class ModelAutoConfigResult(BaseModel):
    """Skipped entry points and backend names that replaced local defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelBackendFinding, ...] = ()
    overrides: dict[str, str] = Field(default_factory=dict)
