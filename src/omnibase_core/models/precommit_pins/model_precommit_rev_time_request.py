# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed input to the rev-time effect."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.models.precommit_pins.model_precommit_rev_time_parameters import (
    ModelPrecommitRevTimeParameters,
)


class ModelPrecommitRevTimeRequest(BaseModel):
    """Candidate pins and contract-owned lookup settings."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    pins: tuple[ModelPrecommitPin, ...]
    parameters: ModelPrecommitRevTimeParameters
    cache_home: str | None = None
