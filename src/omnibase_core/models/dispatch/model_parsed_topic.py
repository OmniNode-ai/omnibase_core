"""
Parsed Topic Model.

Structured result of parsing a topic string for ONEX routing.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_topic_standard import EnumTopicStandard
from omnibase_core.enums.enum_topic_taxonomy import EnumTopicType


class ModelParsedTopic(BaseModel):
    """
    Structured result of parsing a topic string.

    Contains all extracted components from a topic name along with
    validation status and error information. This model enables
    deterministic routing by providing consistent access to topic
    metadata regardless of the original topic format.

    Attributes:
        raw_topic: The original topic string that was parsed.
        standard: The detected topic naming standard.
        domain: The domain extracted from the topic (e.g., 'registration').
        category: The message category (EVENT, COMMAND, INTENT) if detected.
        topic_type: The topic type (events, commands, intents, snapshots) if detected.
        environment: The environment prefix (e.g., 'dev', 'prod') if present.
        version: The version suffix (e.g., 'v1', 'v2') if present.
        is_valid: Whether the topic successfully parsed according to its standard.
        validation_error: Error message if parsing failed.

    Example:
        >>> parsed = ModelParsedTopic(
        ...     raw_topic="onex.registration.events",
        ...     standard=EnumTopicStandard.ONEX_KAFKA,
        ...     domain="registration",
        ...     category=EnumMessageCategory.EVENT,
        ...     topic_type=EnumTopicType.EVENTS,
        ...     is_valid=True,
        ... )
        >>> parsed.is_valid
        True
        >>> parsed.domain
        'registration'
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    # ---- Source ----
    raw_topic: str = Field(
        ...,
        description="The original topic string that was parsed.",
        min_length=1,
    )

    # ---- Detected Standard ----
    standard: EnumTopicStandard = Field(
        ...,
        description="The detected topic naming standard.",
    )

    # ---- Extracted Components ----
    domain: str | None = Field(
        default=None,
        description="The domain extracted from the topic (e.g., 'registration').",
    )
    category: EnumMessageCategory | None = Field(
        default=None,
        description="The message category (EVENT, COMMAND, INTENT) if detected.",
    )
    topic_type: EnumTopicType | None = Field(
        default=None,
        description="The topic type (events, commands, intents, snapshots) if detected.",
    )

    # ---- Environment-Aware Components ----
    environment: str | None = Field(
        default=None,
        description="The environment prefix (e.g., 'dev', 'prod') if present.",
    )
    version: str | None = Field(
        default=None,
        description="The version suffix (e.g., 'v1', 'v2') if present.",
    )

    # ---- Validation Status ----
    is_valid: bool = Field(
        default=False,
        description="Whether the topic successfully parsed according to its standard.",
    )
    validation_error: str | None = Field(
        default=None,
        description="Error message if parsing failed.",
    )

    def is_routable(self) -> bool:
        """
        Check if this parsed topic has sufficient information for routing.

        A topic is routable if it has a valid category, which enables
        deterministic routing to the appropriate handler type.

        Returns:
            True if the topic can be used for routing, False otherwise

        Example:
            >>> parsed = ModelParsedTopic(
            ...     raw_topic="onex.registration.events",
            ...     standard=EnumTopicStandard.ONEX_KAFKA,
            ...     category=EnumMessageCategory.EVENT,
            ...     is_valid=True,
            ... )
            >>> parsed.is_routable()
            True
        """
        return self.is_valid and self.category is not None


__all__ = ["ModelParsedTopic"]
