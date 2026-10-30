# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One remote identity lookup with no ambient configuration."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_dev_tag_lineage_policy import (
    ModelDevTagLineagePolicy,
)


class ModelDevTagLineageRequest(BaseModel):
    """The effect receives all external dependencies in this immutable request."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    policy: ModelDevTagLineagePolicy
