# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved bus operations for a principal."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.event_bus.model_bus_binding import ModelBusBinding
from omnibase_core.models.event_bus.model_bus_group_describe import (
    ModelBusGroupDescribe,
)


class ModelResolvedBusBindings(BaseModel):
    """Unique topic bindings and consumer group inspections for a principal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    principal: str = Field(min_length=1)
    bindings: tuple[ModelBusBinding, ...]
    described_groups: tuple[ModelBusGroupDescribe, ...] = ()

    @model_validator(mode="after")
    def validate_unique_operations(self) -> Self:
        """Reject duplicate binding and group describe identities."""
        binding_keys = {
            (
                binding.broker,
                binding.physical_topic,
                binding.direction,
                binding.consumer_group,
            )
            for binding in self.bindings
        }
        if len(binding_keys) != len(self.bindings):
            raise ValueError("Duplicate bindings are not allowed")
        group_keys = {(item.broker, item.group) for item in self.described_groups}
        if len(group_keys) != len(self.described_groups):
            raise ValueError("Duplicate described_groups are not allowed")
        return self

    def brokers(self) -> tuple[str, ...]:
        """Return sorted unique brokers used by any resolved operation."""
        return tuple(
            sorted(
                {binding.broker for binding in self.bindings}
                | {item.broker for item in self.described_groups}
            )
        )


__all__ = ["ModelResolvedBusBindings"]
