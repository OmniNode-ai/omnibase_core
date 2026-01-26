"""
Topic Metadata Model.

Model for topic subscription/publication metadata in ONEX event bus contracts.
Provides extension point for schema_ref and description per topic.
"""

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
