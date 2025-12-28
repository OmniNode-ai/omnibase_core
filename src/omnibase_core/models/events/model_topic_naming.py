"""
Topic naming model for ONEX message routing.

This module provides ModelTopicNaming, a Pydantic model that generates
canonical Kafka topic names based on domain and message category.

Topic Naming Convention:
    <environment>.<domain>.<category>s.<version>

Examples:
    - dev.omninode-bridge.events.v1
    - prod.user-service.commands.v1
    - staging.payment.intents.v1

Key Design Decisions:
    1. Environment prefix enables multi-tenant isolation
    2. Domain identifies the business domain or service
    3. Category suffix (events/commands/intents) enables message segregation
    4. Version suffix enables schema evolution

See Also:
    - omnibase_core.enums.EnumMessageCategory: Message category enumeration
    - docs/architecture/MESSAGE_TOPIC_MAPPING.md: Comprehensive topic mapping guide
"""

import re
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelTopicNaming(BaseModel):
    """
    Canonical topic naming for ONEX message routing.

    Generates properly formatted Kafka topic names following ONEX conventions.
    Ensures consistent naming across the entire system for proper message
    segregation, routing, and observability.

    Topic Format:
        <environment>.<domain>.<category>s.<version>

    Examples:
        >>> naming = ModelTopicNaming(
        ...     environment="dev",
        ...     domain="user-service",
        ...     category=EnumMessageCategory.EVENT,
        ... )
        >>> naming.topic_name
        'dev.user-service.events.v1'

        >>> naming = ModelTopicNaming(
        ...     environment="prod",
        ...     domain="payment",
        ...     category=EnumMessageCategory.COMMAND,
        ...     version="v2",
        ... )
        >>> naming.topic_name
        'prod.payment.commands.v2'

    Attributes:
        environment: Deployment environment (dev, staging, prod)
        domain: Business domain or service identifier
        category: Message category (EVENT, COMMAND, INTENT)
        version: Topic schema version (default: "v1")

    Properties:
        topic_name: Fully qualified topic name
        topic_suffix: Category-based suffix (events, commands, intents)
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        from_attributes=True,
    )

    # Validation patterns
    DOMAIN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9\-]*$")
    ENVIRONMENT_VALUES: ClassVar[frozenset[str]] = frozenset(
        {"dev", "staging", "prod", "test", "local"}
    )

    environment: str = Field(
        default="dev",
        description="Deployment environment (dev, staging, prod, test, local)",
        min_length=1,
        max_length=20,
    )

    domain: str = Field(
        ...,
        description="Business domain or service identifier (lowercase, hyphen-separated)",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
        examples=["user-service", "payment", "order-management", "omninode-bridge"],
    )

    category: EnumMessageCategory = Field(
        ...,
        description="Message category determining topic suffix",
    )

    version: str = Field(
        default="v1",
        description="Topic schema version (format: v<number>)",
        pattern=r"^v\d+$",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is a known value."""
        v_lower = v.lower()
        if v_lower not in cls.ENVIRONMENT_VALUES:
            valid = ", ".join(sorted(cls.ENVIRONMENT_VALUES))
            msg = f"Environment must be one of: {valid}. Got: {v}"
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)
        return v_lower

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain follows naming convention."""
        v_lower = v.lower()
        if not cls.DOMAIN_PATTERN.match(v_lower):
            msg = (
                f"Domain must start with letter and contain only lowercase letters, "
                f"numbers, and hyphens. Got: {v}"
            )
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)
        return v_lower

    @property
    def topic_name(self) -> str:
        """
        Get the fully qualified topic name.

        Format: <environment>.<domain>.<category>s.<version>

        Returns:
            str: Complete topic name ready for Kafka

        Example:
            >>> naming = ModelTopicNaming(
            ...     environment="dev",
            ...     domain="user",
            ...     category=EnumMessageCategory.EVENT,
            ... )
            >>> naming.topic_name
            'dev.user.events.v1'
        """
        return f"{self.environment}.{self.domain}.{self.category.topic_suffix}.{self.version}"

    @property
    def topic_suffix(self) -> str:
        """
        Get the topic suffix based on message category.

        Returns:
            str: Pluralized category name (events, commands, intents)
        """
        return self.category.topic_suffix

    @classmethod
    def parse_topic(cls, topic: str) -> "ModelTopicNaming | None":
        """
        Parse a topic name into its components.

        Attempts to extract environment, domain, category, and version
        from a fully qualified topic name.

        Args:
            topic: Full topic name to parse

        Returns:
            ModelTopicNaming if parsing succeeds, None otherwise

        Example:
            >>> naming = ModelTopicNaming.parse_topic("dev.user.events.v1")
            >>> naming.domain
            'user'
            >>> naming.category
            <EnumMessageCategory.EVENT: 'event'>
        """
        parts = topic.lower().split(".")
        if len(parts) < 3:
            return None

        # Handle format: <env>.<domain>.<suffix>.<version>
        # or: <env>.<domain>.<suffix>
        environment = parts[0]
        version = "v1"

        # Check if last part is a version
        if parts[-1].startswith("v") and parts[-1][1:].isdigit():
            version = parts[-1]
            suffix = parts[-2]
            domain = ".".join(parts[1:-2]) if len(parts) > 3 else parts[1]
        else:
            suffix = parts[-1]
            domain = ".".join(parts[1:-1]) if len(parts) > 2 else parts[1]

        # Determine category from suffix
        category = EnumMessageCategory.from_topic(f"x.{suffix}")
        if category is None:
            return None

        try:
            return cls(
                environment=environment,
                domain=domain,
                category=category,
                version=version,
            )
        except ValueError:
            return None

    @classmethod
    def for_events(
        cls,
        domain: str,
        environment: str = "dev",
        version: str = "v1",
    ) -> "ModelTopicNaming":
        """
        Create a topic naming for events.

        Args:
            domain: Business domain
            environment: Deployment environment
            version: Topic schema version

        Returns:
            ModelTopicNaming configured for events
        """
        return cls(
            environment=environment,
            domain=domain,
            category=EnumMessageCategory.EVENT,
            version=version,
        )

    @classmethod
    def for_commands(
        cls,
        domain: str,
        environment: str = "dev",
        version: str = "v1",
    ) -> "ModelTopicNaming":
        """
        Create a topic naming for commands.

        Args:
            domain: Business domain
            environment: Deployment environment
            version: Topic schema version

        Returns:
            ModelTopicNaming configured for commands
        """
        return cls(
            environment=environment,
            domain=domain,
            category=EnumMessageCategory.COMMAND,
            version=version,
        )

    @classmethod
    def for_intents(
        cls,
        domain: str,
        environment: str = "dev",
        version: str = "v1",
    ) -> "ModelTopicNaming":
        """
        Create a topic naming for intents.

        Args:
            domain: Business domain
            environment: Deployment environment
            version: Topic schema version

        Returns:
            ModelTopicNaming configured for intents
        """
        return cls(
            environment=environment,
            domain=domain,
            category=EnumMessageCategory.INTENT,
            version=version,
        )


def validate_topic_matches_category(
    topic: str,
    expected_category: EnumMessageCategory,
) -> bool:
    """
    Validate that a topic name matches the expected message category.

    This is a critical enforcement function that ensures messages are
    published to and consumed from the correct topic type.

    Args:
        topic: Kafka topic name to validate
        expected_category: Expected message category

    Returns:
        bool: True if topic matches expected category, False otherwise

    Example:
        >>> validate_topic_matches_category("dev.user.events.v1", EnumMessageCategory.EVENT)
        True
        >>> validate_topic_matches_category("dev.user.commands.v1", EnumMessageCategory.EVENT)
        False

    Raises:
        No exceptions - returns False for invalid topics
    """
    actual_category = EnumMessageCategory.from_topic(topic)
    return actual_category == expected_category


def get_topic_category(topic: str) -> EnumMessageCategory | None:
    """
    Extract the message category from a topic name.

    Args:
        topic: Kafka topic name

    Returns:
        EnumMessageCategory if topic follows convention, None otherwise

    Example:
        >>> get_topic_category("dev.user.events.v1")
        <EnumMessageCategory.EVENT: 'event'>
        >>> get_topic_category("invalid-topic")
        None
    """
    return EnumMessageCategory.from_topic(topic)


def validate_message_topic_alignment(
    topic: str,
    message_category: EnumMessageCategory,
    message_type_name: str | None = None,
) -> None:
    """
    Validate that a message category matches the topic it's being published to.

    This is a runtime enforcement function that ensures messages are published
    to the correct topic type (events to .events topics, commands to .commands, etc.)

    Args:
        topic: Kafka topic name to publish to
        message_category: The category of the message being published
        message_type_name: Optional name of the message type for error context

    Raises:
        ModelOnexError: If the message category doesn't match the topic

    Example:
        >>> validate_message_topic_alignment(
        ...     "dev.user.events.v1",
        ...     EnumMessageCategory.EVENT,
        ... )  # OK - no error

        >>> validate_message_topic_alignment(
        ...     "dev.user.events.v1",
        ...     EnumMessageCategory.COMMAND,
        ... )  # Raises ModelOnexError
    """
    topic_category = EnumMessageCategory.from_topic(topic)

    if topic_category is None:
        raise ModelOnexError(
            message=f"Cannot determine message category from topic: {topic}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "topic": topic,
                "message_category": str(message_category),
                "message_type": message_type_name,
            },
        )

    if topic_category != message_category:
        raise ModelOnexError(
            message=(
                f"Message category mismatch with topic: expected {topic_category.value} "
                f"for topic '{topic}', got {message_category.value}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "topic": topic,
                "expected_category": str(topic_category),
                "actual_category": str(message_category),
                "message_type": message_type_name,
            },
        )
