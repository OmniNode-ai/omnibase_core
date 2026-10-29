# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed output from the rev-time effect."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)


class ModelPrecommitRevTimeResult(BaseModel):
    """Only successfully resolved repository/revision pairs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    rev_times: tuple[ModelPrecommitRevTime, ...]
