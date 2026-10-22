# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output of the validator-triggered emitter (OMN-21277)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_validator_triggered_event import (
    ModelValidatorTriggeredEvent,
)

__all__ = ["ModelValidatorTriggeredEmitOutput"]


class ModelValidatorTriggeredEmitOutput(BaseModel):
    """The events published, one per triggered validator, in report order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    events: tuple[ModelValidatorTriggeredEvent, ...] = Field(default=())
