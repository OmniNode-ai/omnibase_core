# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The run and fire events of one validation report (OMN-17427)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)

__all__ = ["ModelValidatorRunEvents"]


class ModelValidatorRunEvents(BaseModel):
    """The run event and the fire events of one report, run event first."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    events: tuple[ModelValidatorRunEvent, ...]
