# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A client operation to list or describe a consumer group."""

from pydantic import BaseModel, ConfigDict, Field


class ModelBusGroupDescribe(BaseModel):
    """A consumer group inspection on a logical broker."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker: str = Field(min_length=1, description="Logical broker reference.")
    group: str = Field(min_length=1, description="Consumer group to list or describe.")


__all__ = ["ModelBusGroupDescribe"]
