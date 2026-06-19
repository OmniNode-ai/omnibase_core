# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Topic Metadata Model.

Model for topic subscription/publication metadata in ONEX event bus contracts.
Provides extension point for schema_ref, description, and per-topic
provisioning config per topic.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_topic_provisioning_config import (
    ModelTopicProvisioningConfig,
)

__all__ = ["ModelTopicMeta"]


class ModelTopicMeta(BaseModel):
    """
    Metadata for a topic subscription/publication.

    Provides optional metadata for topics declared in publish_topics
    and subscribe_topics fields, keyed by the topic suffix string.
    This is an extension point for future schema validation and
    documentation generation.
    """

    schema_ref: str | None = Field(
        default=None,
        description="Reference to the Pydantic model for this topic's payload",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of this topic's purpose",
    )

    topic_config: ModelTopicProvisioningConfig | None = Field(
        default=None,
        description=(
            "Optional per-topic provisioning config (partitions, "
            "replication_factor, kafka_config). None defers to the platform "
            "ModelTopicSpec defaults."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
