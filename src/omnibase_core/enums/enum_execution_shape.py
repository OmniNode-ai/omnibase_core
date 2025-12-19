"""
Execution Shape Enums.

Enumerations for message categories and canonical execution shapes in ONEX.
Used for validating that execution patterns conform to architectural standards.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumMessageCategory(str, Enum):
    """
    Categories of messages in ONEX for routing and topic mapping.

    Messages in ONEX fall into three semantic categories that determine
    how they should be processed, which node types can handle them, and
    which topics they should be routed to:

    - EVENT: Represents something that happened (past tense, immutable facts)
    - COMMAND: Represents a request to do something (imperative action)
    - INTENT: Represents a desire to achieve an outcome (goal-oriented)

    Topic Mapping:
        Each message category maps to a specific topic suffix pattern:
        - EVENT -> <domain>.events
        - COMMAND -> <domain>.commands
        - INTENT -> <domain>.intents

    Example:
        >>> # Classify a message
        >>> category = EnumMessageCategory.EVENT
        >>> EnumMessageCategory.is_fact_based(category)
        True

        >>> # Check if message is action-oriented
        >>> EnumMessageCategory.is_action_oriented(EnumMessageCategory.COMMAND)
        True

        >>> # Get topic suffix for routing
        >>> category = EnumMessageCategory.EVENT
        >>> print(f"user.{category.topic_suffix}")
        user.events

        >>> # Parse category from topic name
        >>> EnumMessageCategory.from_topic("dev.user.events.v1")
        <EnumMessageCategory.EVENT: 'event'>

        >>> # String serialization
        >>> str(EnumMessageCategory.INTENT)
        'intent'
    """

    EVENT = "event"
    """Something that happened - a past-tense, immutable fact."""

    COMMAND = "command"
    """A request to do something - an imperative action."""

    INTENT = "intent"
    """A desire to achieve an outcome - goal-oriented."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @property
    def topic_suffix(self) -> str:
        """
        Get the topic suffix for this message category.

        Returns:
            str: Pluralized topic suffix (e.g., "events", "commands", "intents")

        Example:
            >>> EnumMessageCategory.EVENT.topic_suffix
            'events'
            >>> EnumMessageCategory.COMMAND.topic_suffix
            'commands'
        """
        return f"{self.value}s"

    @classmethod
    def from_topic(cls, topic: str) -> EnumMessageCategory | None:
        """
        Infer the message category from a topic name.

        Examines the topic to determine the message category by looking for
        category patterns (.events, .commands, .intents) anywhere in the topic.
        This handles both simple topics (user.events) and versioned topics
        (dev.user.events.v1).

        Args:
            topic: Full topic name (e.g., "user.events", "dev.user.events.v1")

        Returns:
            EnumMessageCategory or None if no match found

        Example:
            >>> EnumMessageCategory.from_topic("user.events")
            <EnumMessageCategory.EVENT: 'event'>
            >>> EnumMessageCategory.from_topic("dev.user.events.v1")
            <EnumMessageCategory.EVENT: 'event'>
            >>> EnumMessageCategory.from_topic("prod.order.commands.v2")
            <EnumMessageCategory.COMMAND: 'command'>
            >>> EnumMessageCategory.from_topic("invalid.topic")
            None
        """
        topic_lower = topic.lower()
        # Check for category patterns - handles both .events and .events.v1
        if ".events." in topic_lower or topic_lower.endswith(".events"):
            return cls.EVENT
        if ".commands." in topic_lower or topic_lower.endswith(".commands"):
            return cls.COMMAND
        if ".intents." in topic_lower or topic_lower.endswith(".intents"):
            return cls.INTENT
        return None

    @classmethod
    def is_fact_based(cls, category: EnumMessageCategory) -> bool:
        """
        Check if the message category represents a fact (past tense).

        Args:
            category: The message category to check

        Returns:
            True if it represents a fact, False otherwise
        """
        return category == cls.EVENT

    @classmethod
    def is_action_oriented(cls, category: EnumMessageCategory) -> bool:
        """
        Check if the message category is action-oriented.

        Args:
            category: The message category to check

        Returns:
            True if it's action-oriented, False otherwise
        """
        return category in {cls.COMMAND, cls.INTENT}

    @classmethod
    def is_goal_oriented(cls, category: EnumMessageCategory) -> bool:
        """
        Check if the message category is goal-oriented.

        Args:
            category: The message category to check

        Returns:
            True if it's goal-oriented, False otherwise
        """
        return category == cls.INTENT

    @classmethod
    def get_description(cls, category: EnumMessageCategory) -> str:
        """
        Get a human-readable description of the message category.

        Args:
            category: The message category to describe

        Returns:
            A human-readable description
        """
        descriptions = {
            cls.EVENT: "Something that happened (past-tense, immutable fact)",
            cls.COMMAND: "A request to do something (imperative action)",
            cls.INTENT: "A desire to achieve an outcome (goal-oriented)",
        }
        return descriptions.get(category, "Unknown message category")


@unique
class EnumExecutionShape(str, Enum):
    """
    Canonical execution shapes in ONEX.

    Execution shapes define the valid patterns for message flow between
    node types in the ONEX architecture. Each shape represents a
    validated path from a message category to a target node type.

    The ONEX four-node architecture (EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR)
    has specific valid shapes that enforce architectural compliance.

    Canonical Shapes:
    - EVENT_TO_ORCHESTRATOR: Events routed to orchestrators for workflow coordination
    - EVENT_TO_REDUCER: Events routed to reducers for state aggregation
    - INTENT_TO_EFFECT: Intents routed to effects for external actions
    - COMMAND_TO_ORCHESTRATOR: Commands routed to orchestrators for execution
    - COMMAND_TO_EFFECT: Commands routed to effects for direct execution

    Example:
        >>> # Get execution shape
        >>> shape = EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        >>> EnumExecutionShape.get_source_category(shape)
        EnumMessageCategory.EVENT

        >>> # Check if shape targets a coordinator
        >>> EnumExecutionShape.targets_coordinator(EnumExecutionShape.COMMAND_TO_ORCHESTRATOR)
        True

        >>> # String serialization
        >>> str(EnumExecutionShape.INTENT_TO_EFFECT)
        'intent_to_effect'
    """

    EVENT_TO_ORCHESTRATOR = "event_to_orchestrator"
    """Events routed to orchestrators for workflow coordination."""

    EVENT_TO_REDUCER = "event_to_reducer"
    """Events routed to reducers for state aggregation."""

    INTENT_TO_EFFECT = "intent_to_effect"
    """Intents routed to effects for external actions."""

    COMMAND_TO_ORCHESTRATOR = "command_to_orchestrator"
    """Commands routed to orchestrators for workflow execution."""

    COMMAND_TO_EFFECT = "command_to_effect"
    """Commands routed to effects for direct execution."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_source_category(cls, shape: EnumExecutionShape) -> EnumMessageCategory:
        """
        Get the source message category for an execution shape.

        Args:
            shape: The execution shape to analyze

        Returns:
            The source message category
        """
        source_mapping = {
            cls.EVENT_TO_ORCHESTRATOR: EnumMessageCategory.EVENT,
            cls.EVENT_TO_REDUCER: EnumMessageCategory.EVENT,
            cls.INTENT_TO_EFFECT: EnumMessageCategory.INTENT,
            cls.COMMAND_TO_ORCHESTRATOR: EnumMessageCategory.COMMAND,
            cls.COMMAND_TO_EFFECT: EnumMessageCategory.COMMAND,
        }
        return source_mapping[shape]

    @classmethod
    def get_target_node_kind(cls, shape: EnumExecutionShape) -> str:
        """
        Get the target node kind for an execution shape.

        Returns the string value to avoid circular imports with EnumNodeKind.

        Args:
            shape: The execution shape to analyze

        Returns:
            The target node kind as a string (e.g., 'orchestrator', 'reducer', 'effect')
        """
        target_mapping = {
            cls.EVENT_TO_ORCHESTRATOR: "orchestrator",
            cls.EVENT_TO_REDUCER: "reducer",
            cls.INTENT_TO_EFFECT: "effect",
            cls.COMMAND_TO_ORCHESTRATOR: "orchestrator",
            cls.COMMAND_TO_EFFECT: "effect",
        }
        return target_mapping[shape]

    @classmethod
    def targets_coordinator(cls, shape: EnumExecutionShape) -> bool:
        """
        Check if the execution shape targets a coordination node (orchestrator).

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets an orchestrator, False otherwise
        """
        return shape in {cls.EVENT_TO_ORCHESTRATOR, cls.COMMAND_TO_ORCHESTRATOR}

    @classmethod
    def targets_effect(cls, shape: EnumExecutionShape) -> bool:
        """
        Check if the execution shape targets an effect node.

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets an effect, False otherwise
        """
        return shape in {cls.INTENT_TO_EFFECT, cls.COMMAND_TO_EFFECT}

    @classmethod
    def targets_reducer(cls, shape: EnumExecutionShape) -> bool:
        """
        Check if the execution shape targets a reducer node.

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets a reducer, False otherwise
        """
        return shape == cls.EVENT_TO_REDUCER

    @classmethod
    def get_shapes_for_category(
        cls,
        category: EnumMessageCategory,
    ) -> list[EnumExecutionShape]:
        """
        Get all execution shapes that start with the given message category.

        Args:
            category: The message category to filter by

        Returns:
            List of execution shapes for the category
        """
        return [shape for shape in cls if cls.get_source_category(shape) == category]

    @classmethod
    def get_shapes_for_target(cls, target_kind: str) -> list[EnumExecutionShape]:
        """
        Get all execution shapes that target the given node kind.

        Args:
            target_kind: The target node kind (e.g., 'orchestrator', 'effect', 'reducer')

        Returns:
            List of execution shapes targeting that node kind
        """
        return [
            shape for shape in cls if cls.get_target_node_kind(shape) == target_kind
        ]

    @classmethod
    def get_description(cls, shape: EnumExecutionShape) -> str:
        """
        Get a human-readable description of the execution shape.

        Args:
            shape: The execution shape to describe

        Returns:
            A human-readable description
        """
        descriptions = {
            cls.EVENT_TO_ORCHESTRATOR: "Events routed to orchestrators for workflow coordination",
            cls.EVENT_TO_REDUCER: "Events routed to reducers for state aggregation",
            cls.INTENT_TO_EFFECT: "Intents routed to effects for external actions",
            cls.COMMAND_TO_ORCHESTRATOR: "Commands routed to orchestrators for workflow execution",
            cls.COMMAND_TO_EFFECT: "Commands routed to effects for direct execution",
        }
        return descriptions.get(shape, "Unknown execution shape")


# Export for use
__all__ = ["EnumMessageCategory", "EnumExecutionShape"]
