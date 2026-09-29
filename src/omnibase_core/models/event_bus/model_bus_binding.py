# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A resolved topic binding for a logical broker."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_bus_binding_direction import EnumBusBindingDirection


class ModelBusBinding(BaseModel):
    """A wire topic operation with direction-specific consumer group rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker: str = Field(min_length=1, description="Logical broker reference.")
    physical_topic: str = Field(
        min_length=1, description="Wire topic after tenant prefixing."
    )
    direction: EnumBusBindingDirection
    consumer_group: str | None = None

    @model_validator(mode="after")
    def validate_consumer_group(self) -> Self:
        """Require a group for consuming and forbid one for producing."""
        if self.direction == EnumBusBindingDirection.CONSUME:
            if not self.consumer_group:
                raise ValueError("CONSUME requires a non-empty consumer_group")
        elif self.consumer_group is not None:
            raise ValueError("PRODUCE forbids consumer_group")
        return self


__all__ = ["ModelBusBinding"]
