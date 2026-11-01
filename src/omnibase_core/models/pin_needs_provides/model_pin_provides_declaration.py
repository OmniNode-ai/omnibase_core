# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The callers' provides declaration, read as data (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.pin_needs_provides.model_pin_caller import ModelPinCaller


class ModelPinProvidesDeclaration(BaseModel):
    """Every declared caller; one caller path is declared once."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    callers: tuple[ModelPinCaller, ...] = Field(
        default_factory=tuple, description="Declared callers"
    )

    @model_validator(mode="after")
    def _one_entry_per_caller(self) -> ModelPinProvidesDeclaration:
        paths = [entry.caller for entry in self.callers]
        if len(paths) != len(set(paths)):
            raise ValueError("one caller is declared twice")
        return self

    def caller_for(self, source_name: str) -> ModelPinCaller | None:
        """The entry of the caller at ``source_name``, the longest matching path first."""
        matches = [entry for entry in self.callers if entry.names(source_name)]
        return max(matches, key=lambda entry: len(entry.caller), default=None)
