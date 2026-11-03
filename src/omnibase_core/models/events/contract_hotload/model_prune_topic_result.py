# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a prune did with one candidate topic (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_prune_topic_status import EnumPruneTopicStatus

__all__ = ["ModelPruneTopicResult"]


class ModelPruneTopicResult(BaseModel):
    """What a prune did with one candidate topic.

    Attributes:
        topic: The candidate topic.
        status: ``retired``, ``skipped`` or ``failed``.
        retired_topic_id: The id the topic was retired under, for a retired topic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(min_length=1)
    status: EnumPruneTopicStatus
    retired_topic_id: UUID | None = None
