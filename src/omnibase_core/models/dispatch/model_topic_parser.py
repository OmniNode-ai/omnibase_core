"""
Topic Parser for ONEX Deterministic Routing.

Provides structured parsing of ONEX topic names to support deterministic routing
based on topic category. Handles both ONEX Kafka format (onex.<domain>.<type>)
and Environment-Aware format (<env>.<domain>.<category>.<version>).

Design Pattern:
    ModelTopicParser is a stateless utility class that provides topic parsing
    and pattern matching capabilities. It extracts structured information from
    topic strings including:
    - Topic standard detection (ONEX Kafka vs Environment-Aware)
    - Domain extraction
    - Message category inference (EVENT, COMMAND, INTENT)
    - Topic type (events, commands, intents, snapshots)
    - Environment and version (for Environment-Aware format)

    This enables deterministic routing decisions based on topic structure
    without requiring handler registration lookups.

Thread Safety:
    ModelTopicParser is stateless and all methods are pure functions,
    making it fully thread-safe for concurrent access.

Example:
    >>> from omnibase_core.models.dispatch import ModelTopicParser, ModelParsedTopic
    >>>
    >>> parser = ModelTopicParser()
    >>>
    >>> # Parse ONEX Kafka format
    >>> result = parser.parse("onex.registration.events")
    >>> result.domain
    'registration'
    >>> result.category
    <EnumMessageCategory.EVENT: 'event'>
    >>>
    >>> # Parse Environment-Aware format
    >>> result = parser.parse("dev.user.events.v1")
    >>> result.environment
    'dev'
    >>> result.version
    'v1'
    >>>
    >>> # Get category for routing
    >>> parser.get_category("onex.registration.commands")
    <EnumMessageCategory.COMMAND: 'command'>
    >>>
    >>> # Pattern matching
    >>> parser.matches_pattern("onex.*.events", "onex.registration.events")
    True

See Also:
    omnibase_core.enums.EnumMessageCategory: Message category enum
    omnibase_core.enums.EnumTopicType: Topic type enum
    omnibase_core.constants.constants_topic_taxonomy: Topic naming constants
"""

import re
from functools import cached_property

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_topic_standard import EnumTopicStandard
from omnibase_core.enums.enum_topic_taxonomy import EnumTopicType
from omnibase_core.models.dispatch.model_parsed_topic import ModelParsedTopic


class ModelTopicParser:
    """
    Parser for ONEX topic names supporting multiple format standards.

    Provides structured parsing of topic strings to extract routing-relevant
    information. Supports both ONEX Kafka format (onex.<domain>.<type>) and
    Environment-Aware format (<env>.<domain>.<category>.<version>).

    The parser is stateless and all methods are pure functions, making it
    safe for concurrent use across threads.

    Patterns:
        - ONEX Kafka: onex.<domain>.<type>
          Examples: onex.registration.events, onex.discovery.commands
        - Environment-Aware: <env>.<domain>.<category>.<version>
          Examples: dev.user.events.v1, prod.order.commands.v2

    Example:
        >>> parser = ModelTopicParser()
        >>>
        >>> # Parse and extract category for routing
        >>> category = parser.get_category("onex.registration.events")
        >>> category
        <EnumMessageCategory.EVENT: 'event'>
        >>>
        >>> # Check pattern matching
        >>> parser.matches_pattern("onex.*.events", "onex.registration.events")
        True
        >>> parser.matches_pattern("**.events", "dev.user.events.v1")
        True
    """

    # ONEX Kafka format: onex.<domain>.<type>
    # Domain: lowercase alphanumeric with hyphens, starting with letter
    # Type: one of commands, events, intents, snapshots
    _ONEX_KAFKA_PATTERN = re.compile(
        r"^onex\.(?P<domain>[a-z][a-z0-9-]*[a-z0-9]|[a-z])\."
        r"(?P<type>commands|events|intents|snapshots)$",
        re.IGNORECASE,
    )

    # Environment-Aware format: <env>.<domain>.<category>.<version>
    # Env: dev, prod, staging, test, local (case-insensitive)
    # Domain: alphanumeric with hyphens
    # Category: events, commands, intents (plural form)
    # Version: v followed by digits
    _ENV_AWARE_PATTERN = re.compile(
        r"^(?P<env>dev|prod|staging|test|local)\."
        r"(?P<domain>[a-z][a-z0-9-]*[a-z0-9]|[a-z])\."
        r"(?P<category>commands|events|intents)\."
        r"(?P<version>v\d+)$",
        re.IGNORECASE,
    )

    # Domain validation pattern (reused from constants_topic_taxonomy)
    _DOMAIN_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")

    # Valid topic types for validation
    _VALID_TOPIC_TYPES = frozenset({"commands", "events", "intents", "snapshots"})

    # Mapping from topic type suffix to EnumTopicType
    _TOPIC_TYPE_MAP: dict[str, EnumTopicType] = {
        "commands": EnumTopicType.COMMANDS,
        "events": EnumTopicType.EVENTS,
        "intents": EnumTopicType.INTENTS,
        "snapshots": EnumTopicType.SNAPSHOTS,
    }

    # Mapping from topic type suffix to EnumMessageCategory
    # Note: snapshots don't have a direct category mapping
    _CATEGORY_MAP: dict[str, EnumMessageCategory] = {
        "commands": EnumMessageCategory.COMMAND,
        "events": EnumMessageCategory.EVENT,
        "intents": EnumMessageCategory.INTENT,
    }

    def parse(self, topic: str) -> ModelParsedTopic:
        """
        Parse a topic string and extract structured information.

        Attempts to parse the topic against known formats (ONEX Kafka and
        Environment-Aware) and returns a structured result with all extracted
        components.

        Args:
            topic: The topic string to parse

        Returns:
            ModelParsedTopic with extracted components and validation status

        Example:
            >>> parser = ModelTopicParser()
            >>> result = parser.parse("onex.registration.events")
            >>> result.standard
            <EnumTopicStandard.ONEX_KAFKA: 'onex_kafka'>
            >>> result.domain
            'registration'
            >>> result.category
            <EnumMessageCategory.EVENT: 'event'>
        """
        if not topic or not topic.strip():
            return ModelParsedTopic(
                raw_topic=topic if topic else "<empty>",
                standard=EnumTopicStandard.UNKNOWN,
                is_valid=False,
                validation_error="Topic cannot be empty or whitespace",
            )

        topic_stripped = topic.strip()

        # Try ONEX Kafka format first (canonical)
        onex_match = self._ONEX_KAFKA_PATTERN.match(topic_stripped)
        if onex_match:
            return self._parse_onex_kafka(topic_stripped, onex_match)

        # Try Environment-Aware format
        env_match = self._ENV_AWARE_PATTERN.match(topic_stripped)
        if env_match:
            return self._parse_env_aware(topic_stripped, env_match)

        # Fallback: Try to extract category using existing EnumMessageCategory.from_topic
        # This handles partial matches and legacy formats
        category = EnumMessageCategory.from_topic(topic_stripped)
        if category is not None:
            # Extract domain by finding the category suffix position
            topic_lower = topic_stripped.lower()
            category_suffix = f".{category.topic_suffix}"
            if category_suffix in topic_lower:
                # Find the domain: everything before the category suffix
                suffix_idx = topic_lower.find(category_suffix)
                prefix = topic_stripped[:suffix_idx]
                # Remove environment prefix if present
                parts = prefix.split(".")
                domain = parts[-1] if parts else None
                env = parts[0] if len(parts) > 1 else None

                return ModelParsedTopic(
                    raw_topic=topic_stripped,
                    standard=EnumTopicStandard.UNKNOWN,
                    domain=domain,
                    category=category,
                    environment=env,
                    is_valid=True,  # Partially valid - category extracted
                )

        # Unknown format
        return ModelParsedTopic(
            raw_topic=topic_stripped,
            standard=EnumTopicStandard.UNKNOWN,
            is_valid=False,
            validation_error=(
                f"Topic '{topic_stripped}' does not match any known format. "
                "Expected: onex.<domain>.<type> or <env>.<domain>.<category>.<version>"
            ),
        )

    def _parse_onex_kafka(self, topic: str, match: re.Match[str]) -> ModelParsedTopic:
        """Parse ONEX Kafka format: onex.<domain>.<type>."""
        domain = match.group("domain").lower()
        type_str = match.group("type").lower()

        topic_type = self._TOPIC_TYPE_MAP.get(type_str)
        category = self._CATEGORY_MAP.get(type_str)

        return ModelParsedTopic(
            raw_topic=topic,
            standard=EnumTopicStandard.ONEX_KAFKA,
            domain=domain,
            category=category,
            topic_type=topic_type,
            is_valid=True,
        )

    def _parse_env_aware(self, topic: str, match: re.Match[str]) -> ModelParsedTopic:
        """Parse Environment-Aware format: <env>.<domain>.<category>.<version>."""
        environment = match.group("env").lower()
        domain = match.group("domain").lower()
        category_str = match.group("category").lower()
        version = match.group("version").lower()

        topic_type = self._TOPIC_TYPE_MAP.get(category_str)
        category = self._CATEGORY_MAP.get(category_str)

        return ModelParsedTopic(
            raw_topic=topic,
            standard=EnumTopicStandard.ENVIRONMENT_AWARE,
            domain=domain,
            category=category,
            topic_type=topic_type,
            environment=environment,
            version=version,
            is_valid=True,
        )

    def get_category(self, topic: str) -> EnumMessageCategory | None:
        """
        Extract the message category from a topic for routing.

        This is a convenience method that parses the topic and returns
        just the category, which is the primary input for deterministic
        routing decisions.

        Args:
            topic: The topic string to analyze

        Returns:
            EnumMessageCategory if detected, None otherwise

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.get_category("onex.registration.events")
            <EnumMessageCategory.EVENT: 'event'>
            >>> parser.get_category("dev.user.commands.v1")
            <EnumMessageCategory.COMMAND: 'command'>
            >>> parser.get_category("invalid.topic")
            None
        """
        parsed = self.parse(topic)
        return parsed.category

    def matches_pattern(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic matches a glob-style pattern.

        Supports the following wildcards:
        - '*' (single asterisk): Matches any single segment (no dots)
        - '**' (double asterisk): Matches any number of segments (including dots)

        Pattern matching is case-insensitive.

        Args:
            pattern: The glob pattern to match against
            topic: The topic to check

        Returns:
            True if the topic matches the pattern, False otherwise

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.matches_pattern("onex.*.events", "onex.registration.events")
            True
            >>> parser.matches_pattern("onex.*.events", "onex.discovery.events")
            True
            >>> parser.matches_pattern("onex.*.events", "onex.discovery.commands")
            False
            >>> parser.matches_pattern("**.events", "dev.user.events.v1")
            False  # ** matches segments but v1 is after .events
            >>> parser.matches_pattern("**.events.*", "dev.user.events.v1")
            True
            >>> parser.matches_pattern("dev.**", "dev.user.events.v1")
            True
        """
        if not pattern or not topic:
            return False

        # Compile pattern to regex
        regex_pattern = self._pattern_to_regex(pattern)
        return bool(regex_pattern.match(topic))

    @cached_property
    def _pattern_cache(self) -> dict[str, re.Pattern[str]]:
        """Cache for compiled patterns."""
        return {}

    def _pattern_to_regex(self, pattern: str) -> re.Pattern[str]:
        """
        Convert a glob-style pattern to a compiled regex.

        Handles:
        - '*' -> matches any single segment (no dots)
        - '**' -> matches any number of segments (including empty)
        """
        # Check cache first
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]

        # Handle ** first (must be done before single *)
        # Use a placeholder to avoid double-processing
        escaped = pattern.replace("**", "__DOUBLE_STAR__")

        # Escape special regex characters except *
        escaped = re.escape(escaped)

        # Convert back ** placeholder to multi-segment match
        # ** matches zero or more segments: (?:[^.]+(?:\.[^.]+)*)?
        # This matches: nothing, or one segment, or multiple segments separated by dots
        escaped = escaped.replace("__DOUBLE_STAR__", "(?:[^.]+(?:\\.[^.]+)*)?")

        # Convert single * to single-segment match (no dots)
        escaped = escaped.replace(r"\*", "[^.]+")

        # Compile and cache
        compiled = re.compile(f"^{escaped}$", re.IGNORECASE)
        # Note: cached_property creates dict on first access, but we need to
        # update it. Since this is for optimization only, we can use a class-level
        # cache instead. For simplicity in this implementation, we'll just return
        # the compiled pattern without caching (the cached_property above is unused).
        return compiled

    def validate_topic(
        self, topic: str, strict: bool = False
    ) -> tuple[bool, str | None]:
        """
        Validate a topic string against ONEX standards.

        Args:
            topic: The topic string to validate
            strict: If True, requires exact match to ONEX Kafka format.
                   If False, accepts any format that yields a valid category.

        Returns:
            Tuple of (is_valid, error_message).
            - (True, None) if valid
            - (False, error_message) if invalid

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.validate_topic("onex.registration.events")
            (True, None)
            >>> parser.validate_topic("onex.registration.events", strict=True)
            (True, None)
            >>> parser.validate_topic("dev.user.events.v1")
            (True, None)
            >>> parser.validate_topic("dev.user.events.v1", strict=True)
            (False, "Topic 'dev.user.events.v1' does not match ONEX Kafka format...")
            >>> parser.validate_topic("invalid")
            (False, "Topic 'invalid' does not match any known format...")
        """
        parsed = self.parse(topic)

        if strict:
            if parsed.standard != EnumTopicStandard.ONEX_KAFKA:
                return (
                    False,
                    f"Topic '{topic}' does not match ONEX Kafka format "
                    f"(onex.<domain>.<type>). Detected standard: {parsed.standard.value}",
                )
            return (True, None)

        # Non-strict: accept any valid parsed topic
        if parsed.is_valid:
            return (True, None)

        return (False, parsed.validation_error)

    def is_onex_kafka_format(self, topic: str) -> bool:
        """
        Check if a topic follows the ONEX Kafka naming standard.

        Args:
            topic: The topic string to check

        Returns:
            True if the topic matches onex.<domain>.<type> format

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.is_onex_kafka_format("onex.registration.events")
            True
            >>> parser.is_onex_kafka_format("dev.user.events.v1")
            False
        """
        return bool(self._ONEX_KAFKA_PATTERN.match(topic.strip()))

    def is_environment_aware_format(self, topic: str) -> bool:
        """
        Check if a topic follows the Environment-Aware naming standard.

        Args:
            topic: The topic string to check

        Returns:
            True if the topic matches <env>.<domain>.<category>.<version> format

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.is_environment_aware_format("dev.user.events.v1")
            True
            >>> parser.is_environment_aware_format("onex.registration.events")
            False
        """
        return bool(self._ENV_AWARE_PATTERN.match(topic.strip()))

    def extract_domain(self, topic: str) -> str | None:
        """
        Extract the domain from a topic string.

        Args:
            topic: The topic string to analyze

        Returns:
            The domain name if extractable, None otherwise

        Example:
            >>> parser = ModelTopicParser()
            >>> parser.extract_domain("onex.registration.events")
            'registration'
            >>> parser.extract_domain("dev.user.events.v1")
            'user'
        """
        parsed = self.parse(topic)
        return parsed.domain


# Re-export from split module
from omnibase_core.enums.enum_topic_standard import (
    EnumTopicStandard,  # noqa: F811
)
from omnibase_core.models.dispatch.model_parsed_topic import (
    ModelParsedTopic,
)

__all__ = [
    "EnumTopicStandard",
    "ModelParsedTopic",
    "ModelTopicParser",
]
