# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A validator-runtime overlay: the profile and the bus the runtime binds (OMN-21529)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus_binding import (
    ModelValidatorRuntimeBusBinding,
)

__all__ = ["ModelValidatorRuntimeOverlay", "ValidationProfile"]

# The profiles ``ModelValidationRequestRef`` accepts.
ValidationProfile = Literal["strict", "default", "advisory"]


class ModelValidatorRuntimeOverlay(BaseModel):
    """The named validator-runtime overlay pair differs only in ``bus``."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(min_length=1, description="Overlay family; shared by the pair.")
    profile: ValidationProfile = Field(
        description="Request profile recorded in every report."
    )
    bus: ModelValidatorRuntimeBusBinding
