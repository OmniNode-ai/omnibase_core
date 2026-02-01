"""
Topic Manifest Model for ONEX Domain Topic Configuration.

Defines the structure for declaring domain topics with retention,
compaction, and partitioning policies per OMN-939 topic taxonomy.

Topic naming convention: onex.<domain>.<type>
Example: onex.registration.events, onex.registration.snapshots
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_topic_taxonomy import EnumTopicType
from omnibase_core.models.events.model_topic_config import ModelTopicConfig


class ModelTopicManifest(BaseModel):
    """
    Manifest defining all topics for a domain.

    A topic manifest declares the complete set of topics required
    for a domain, including their configurations. Used by topic
    creation scripts and runtime routing.

    Thread Safety:
        This model is immutable (frozen=True) and thread-safe after instantiation.
        Instances can be safely shared across threads without synchronization.

    Example:
        manifest = ModelTopicManifest.registration_domain()
        for topic_type in manifest.topics:
            topic_name = manifest.get_topic_name(topic_type)
            # Creates: onex.registration.events, onex.registration.commands, etc.

    See Also:
        - docs/standards/onex_topic_taxonomy.md for topic naming conventions
        - docs/guides/THREADING.md for thread safety guidelines
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    domain: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$",
        description="Domain name (lowercase, alphanumeric with hyphens)",
        examples=["registration", "codegen", "metrics"],
    )
    topics: dict[EnumTopicType, ModelTopicConfig] = Field(
        ...,
        description="Topic configurations keyed by topic type",
    )

    def get_topic_name(self, topic_type: EnumTopicType) -> str:
        """
        Generate full topic name using ONEX naming convention.

        Format: onex.<domain>.<type>

        Args:
            topic_type: The topic type to generate name for

        Returns:
            Full topic name (e.g., 'onex.registration.events')

        Raises:
            KeyError: If topic_type not in manifest
        """
        if topic_type not in self.topics:
            # error-ok: KeyError is semantically correct for missing dict key lookup
            raise KeyError(
                f"Topic type '{topic_type}' not defined in manifest for domain '{self.domain}'"
            )
        return f"onex.{self.domain}.{topic_type.value}"

    def get_all_topic_names(self) -> dict[EnumTopicType, str]:
        """
        Get all topic names for this domain.

        Returns:
            Dictionary mapping topic types to their full names
        """
        return {
            topic_type: self.get_topic_name(topic_type) for topic_type in self.topics
        }

    def get_config(self, topic_type: EnumTopicType) -> ModelTopicConfig:
        """
        Get configuration for a specific topic type.

        Args:
            topic_type: The topic type to get configuration for

        Returns:
            Topic configuration

        Raises:
            KeyError: If topic_type not in manifest
        """
        if topic_type not in self.topics:
            # error-ok: KeyError is semantically correct for missing dict key lookup
            raise KeyError(
                f"Topic type '{topic_type}' not defined in manifest for domain '{self.domain}'"
            )
        return self.topics[topic_type]

    @classmethod
    def registration_domain(cls) -> "ModelTopicManifest":
        """
        Topic manifest for the registration domain.

        The registration domain handles node registration,
        discovery, and lifecycle management.
        """
        return cls(
            domain="registration",
            topics={
                EnumTopicType.COMMANDS: ModelTopicConfig.commands_default(),
                EnumTopicType.DLQ: ModelTopicConfig.dlq_default(),
                EnumTopicType.EVENTS: ModelTopicConfig.events_default(),
                EnumTopicType.INTENTS: ModelTopicConfig.intents_default(),
                EnumTopicType.SNAPSHOTS: ModelTopicConfig.snapshots_default(),
            },
        )

    @classmethod
    def create_standard_manifest(cls, domain: str) -> "ModelTopicManifest":
        """
        Create a standard topic manifest for any domain.

        Creates all five topic types with default configurations.

        Args:
            domain: Domain name (lowercase, alphanumeric with hyphens)

        Returns:
            Topic manifest with standard configuration
        """
        return cls(
            domain=domain,
            topics={
                EnumTopicType.COMMANDS: ModelTopicConfig.commands_default(),
                EnumTopicType.DLQ: ModelTopicConfig.dlq_default(),
                EnumTopicType.EVENTS: ModelTopicConfig.events_default(),
                EnumTopicType.INTENTS: ModelTopicConfig.intents_default(),
                EnumTopicType.SNAPSHOTS: ModelTopicConfig.snapshots_default(),
            },
        )


__all__ = [
    "ModelTopicManifest",
]
