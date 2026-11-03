# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Completion of one prune (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_hotload.model_prune_topic_result import (
    ModelPruneTopicResult,
)

__all__ = ["ModelPruneCompletion"]


class ModelPruneCompletion(BaseModel):
    """The per-topic results of one prune, keyed by the prune id.

    Attributes:
        entity_id: The prune id of the request this completes.
        results: One result per candidate topic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    results: tuple[ModelPruneTopicResult, ...]
