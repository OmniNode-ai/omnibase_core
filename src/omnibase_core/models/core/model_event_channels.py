# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Event channels model for node introspection.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventChannels(BaseModel):
    """Model for event channel specification in introspection."""

    subscribes_to: list[str] = Field(
        default_factory=list,
        description="Event channels this node subscribes to for receiving events",
    )
    publishes_to: list[str] = Field(
        default_factory=list,
        description="Event channels this node publishes events to",
    )

    model_config = ConfigDict(extra="forbid")
