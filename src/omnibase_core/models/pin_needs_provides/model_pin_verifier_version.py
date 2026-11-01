# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What one version of a verifier declares it needs (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pin_needs_provides.model_pin_need import ModelPinNeed


class ModelPinVerifierVersion(BaseModel):
    """A pinnable version and its needs; absent needs mean undeclared, never empty."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: str = Field(
        min_length=1, description="Pin value exactly as a caller writes it"
    )
    needs: tuple[ModelPinNeed, ...] | None = Field(
        default=None,
        description="Declared needs; an empty list declares none, an absent one is refused",
    )
