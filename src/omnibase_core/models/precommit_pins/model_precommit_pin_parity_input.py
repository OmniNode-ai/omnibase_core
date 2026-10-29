# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure input to the pre-commit pin-parity check (OMN-21495)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.precommit_pins.model_precommit_pin_rules import (
    ModelPrecommitPinRules,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)

__all__ = ["ModelPrecommitPinParityInput"]


class ModelPrecommitPinParityInput(BaseModel):
    """Rule data, config source and commit times supplied by the caller."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rules: ModelPrecommitPinRules
    path: str
    source: str
    rev_times: tuple[ModelPrecommitRevTime, ...] = ()
