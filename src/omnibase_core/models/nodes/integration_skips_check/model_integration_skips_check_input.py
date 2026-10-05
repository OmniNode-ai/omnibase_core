# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed observations for the integration-skips COMPUTE handler."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.integration_skips_check.model_integration_skip_record import (
    ModelIntegrationSkipRecord,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_config import (
    ModelIntegrationSkipsCheckConfig,
)


class ModelIntegrationSkipsCheckInput(BaseModel):
    """Aggregate counts and skipped records from one or more JUnit artifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    executed: int = Field(default=0, ge=0)
    total_cases: int = Field(default=0, ge=0)
    skipped: tuple[ModelIntegrationSkipRecord, ...] = ()
    config: ModelIntegrationSkipsCheckConfig = Field(
        default_factory=ModelIntegrationSkipsCheckConfig
    )
    strict: bool = False
