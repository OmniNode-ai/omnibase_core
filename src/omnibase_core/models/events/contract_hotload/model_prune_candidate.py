# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One topic a prune request names for retirement (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_hotload.model_partition_end_offset import (
    ModelPartitionEndOffset,
)

__all__ = ["ModelPruneCandidate"]


class ModelPruneCandidate(BaseModel):
    """One topic proposed for retirement, with what the caller saw on it.

    Attributes:
        topic: The topic name.
        end_offsets: The end offset of every partition at the time of the read.
        consumer_groups: The groups that were members of the topic at the time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(min_length=1)
    end_offsets: tuple[ModelPartitionEndOffset, ...]
    consumer_groups: tuple[str, ...]
