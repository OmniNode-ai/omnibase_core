# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The end offset of one partition of a prune candidate (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPartitionEndOffset"]


class ModelPartitionEndOffset(BaseModel):
    """The end offset of one partition, as the caller read it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    partition: int = Field(ge=0)
    end_offset: int = Field(ge=0)
