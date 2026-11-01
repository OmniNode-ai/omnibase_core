# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What one caller declares it provides to the verifiers it pins (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pin_needs_provides.model_pin_need import ModelPinNeed


class ModelPinCaller(BaseModel):
    """A caller file and its provides; absent provides mean undeclared, never empty."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    caller: str = Field(
        min_length=1, description="Caller file path, relative to its repository root"
    )
    provides: tuple[ModelPinNeed, ...] | None = Field(
        default=None,
        description="Declared provides; an empty list provides nothing, an absent one is refused",
    )

    def names(self, source_name: str) -> bool:
        """Whether this entry is the caller at ``source_name``."""
        return source_name == self.caller or source_name.endswith("/" + self.caller)
