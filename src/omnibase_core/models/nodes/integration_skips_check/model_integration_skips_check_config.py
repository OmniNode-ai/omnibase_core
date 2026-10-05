# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed configuration consumed by the pure artifact guard."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.integration_skips_check.model_integration_skip_service_config import (
    ModelIntegrationSkipServiceConfig,
)


class ModelIntegrationSkipsCheckConfig(BaseModel):
    """Provisioning assumptions, optional patterns, and executed minimum."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    silent_skip_allowed: bool = False
    require_executed_min: int = 1
    required_services: dict[str, ModelIntegrationSkipServiceConfig] = Field(
        default_factory=dict
    )
    allowed_optional_skip_patterns: tuple[str, ...] = ()
