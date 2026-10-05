# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Missing-service patterns supplied by the caller."""

from pydantic import BaseModel, ConfigDict


class ModelIntegrationSkipServiceConfig(BaseModel):
    """Case-insensitive patterns for one provisioned service."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    missing_skip_patterns: tuple[str, ...] = ()
