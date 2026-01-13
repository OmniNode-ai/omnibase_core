"""
Execution Shape Enums.

Enumerations for message categories and canonical execution shapes in ONEX.
Used for validating that execution patterns conform to architectural standards.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMessageCategory(StrValueHelper, str, Enum):
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
    def from_topic(cls, topic: str) -> "EnumMessageCategory | None":
        """
        Infer the message category from a topic name.

        Examines the topic to determine the message category by looking for
        category patterns (.events, .commands, .intents) anywhere in the topic.
        This handles both simple topics (user.events) and versioned topics
        (dev.user.events.v1).

        Note:
            Topic matching is case-insensitive. Both "user.EVENTS" and
            "user.events" will correctly return EnumMessageCategory.EVENT.

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
            >>> EnumMessageCategory.from_topic("USER.EVENTS")  # Case-insensitive
            <EnumMessageCategory.EVENT: 'event'>
            >>> EnumMessageCategory.from_topic("invalid.topic")
            None
        """
        topic_lower = topic.lower()
        # Check for category patterns using two complementary conditions:
        # 1. ".events." (with trailing dot) - matches versioned topics like
        #    "user.events.v1" where the category appears mid-string
        # 2. ".endswith('.events')" - matches simple topics like "user.events"
        #    where the category is at the end (no trailing dot)
        # Both checks are necessary because ".events." won't match topics
        # ending with ".events", and endswith won't match versioned topics.
        if ".events." in topic_lower or topic_lower.endswith(".events"):
            return cls.EVENT
        if ".commands." in topic_lower or topic_lower.endswith(".commands"):
            return cls.COMMAND
        if ".intents." in topic_lower or topic_lower.endswith(".intents"):
            return cls.INTENT
        return None

    @classmethod
    def try_from_topic(
        cls, topic: str
    ) -> tuple["EnumMessageCategory | None", str | None]:
        """
        Safely parse a topic name to infer the message category with error context.

        This is a Result-style variant of from_topic() that provides explicit
        error information when parsing fails, useful for validation pipelines
        and error reporting.

        Note:
            Case Sensitivity: Topic matching is case-insensitive. All input
            topics are converted to lowercase before pattern matching.

        Args:
            topic: Full topic name (e.g., "user.events", "dev.user.events.v1")

        Returns:
            A tuple of (category, error_message):
            - On success: (EnumMessageCategory, None)
            - On failure: (None, descriptive error message)

        Example:
            >>> category, error = EnumMessageCategory.try_from_topic("user.events")
            >>> assert category == EnumMessageCategory.EVENT
            >>> assert error is None

            >>> category, error = EnumMessageCategory.try_from_topic("invalid.topic")
            >>> assert category is None
            >>> assert "No message category pattern found" in error
        """
        if not topic:
            return (None, "Empty topic string provided")

        if not topic.strip():
            return (None, "Topic string contains only whitespace")

        category = cls.from_topic(topic)
        if category is not None:
            return (category, None)

        return (
            None,
            f"No message category pattern found in topic '{topic}'. "
            f"Expected topic to contain one of: .events, .commands, .intents",
        )

    @classmethod
    def is_fact_based(cls, category: "EnumMessageCategory") -> bool:
        """
        Check if the message category represents a fact (past tense).

        Only EVENT messages represent facts - immutable records of something
        that has already happened.

        Args:
            category: The message category to check

        Returns:
            True if it represents a fact, False otherwise

        Example:
            >>> EnumMessageCategory.is_fact_based(EnumMessageCategory.EVENT)
            True
            >>> EnumMessageCategory.is_fact_based(EnumMessageCategory.COMMAND)
            False
        """
        return category == cls.EVENT

    @classmethod
    def is_action_oriented(cls, category: "EnumMessageCategory") -> bool:
        """
        Check if the message category is action-oriented.

        Both COMMAND and INTENT messages are action-oriented - they express
        a desire for something to happen, rather than recording what has
        already occurred.

        Args:
            category: The message category to check

        Returns:
            True if it's action-oriented (COMMAND or INTENT), False otherwise

        Example:
            >>> EnumMessageCategory.is_action_oriented(EnumMessageCategory.COMMAND)
            True
            >>> EnumMessageCategory.is_action_oriented(EnumMessageCategory.INTENT)
            True
            >>> EnumMessageCategory.is_action_oriented(EnumMessageCategory.EVENT)
            False
        """
        return category in {cls.COMMAND, cls.INTENT}

    @classmethod
    def is_goal_oriented(cls, category: "EnumMessageCategory") -> bool:
        """
        Check if the message category is goal-oriented.

        Only INTENT messages are goal-oriented - they express a desired
        outcome without specifying how to achieve it. This differs from
        COMMAND messages, which are imperative requests for specific actions.

        Args:
            category: The message category to check

        Returns:
            True if it's goal-oriented, False otherwise

        Example:
            >>> EnumMessageCategory.is_goal_oriented(EnumMessageCategory.INTENT)
            True
            >>> EnumMessageCategory.is_goal_oriented(EnumMessageCategory.COMMAND)
            False
        """
        return category == cls.INTENT

    @classmethod
    def get_description(cls, category: "EnumMessageCategory") -> str:
        """
        Get a human-readable description of the message category.

        Args:
            category: The message category to describe

        Returns:
            A human-readable description of the category's purpose and semantics

        Example:
            >>> EnumMessageCategory.get_description(EnumMessageCategory.EVENT)
            'Something that happened (past-tense, immutable fact)'
            >>> EnumMessageCategory.get_description(EnumMessageCategory.COMMAND)
            'A request to do something (imperative action)'
        """
        descriptions = {
            cls.EVENT: "Something that happened (past-tense, immutable fact)",
            cls.COMMAND: "A request to do something (imperative action)",
            cls.INTENT: "A desire to achieve an outcome (goal-oriented)",
        }
        return descriptions.get(category, "Unknown message category")


@unique
class EnumExecutionShape(StrValueHelper, str, Enum):
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

    @classmethod
    def get_source_category(cls, shape: "EnumExecutionShape") -> EnumMessageCategory:
        """
        Get the source message category for an execution shape.

        Each execution shape has a specific message category that initiates it.
        This method extracts that source category from the shape definition.

        Args:
            shape: The execution shape to analyze

        Returns:
            The source message category (EVENT, COMMAND, or INTENT)

        Example:
            >>> EnumExecutionShape.get_source_category(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            <EnumMessageCategory.EVENT: 'event'>
            >>> EnumExecutionShape.get_source_category(EnumExecutionShape.COMMAND_TO_EFFECT)
            <EnumMessageCategory.COMMAND: 'command'>
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
    def get_target_node_kind(cls, shape: "EnumExecutionShape") -> str:
        """
        Get the target node kind for an execution shape.

        Each execution shape routes to a specific node type. This method
        returns the target node kind as a string to avoid circular imports
        with EnumNodeKind.

        Note:
            Returns a lowercase string matching EnumNodeKind values. Use
            EnumNodeKind(result) to convert to an enum if needed.

        Args:
            shape: The execution shape to analyze

        Returns:
            The target node kind as a string (e.g., 'orchestrator', 'reducer', 'effect')

        Example:
            >>> EnumExecutionShape.get_target_node_kind(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            'orchestrator'
            >>> EnumExecutionShape.get_target_node_kind(EnumExecutionShape.INTENT_TO_EFFECT)
            'effect'
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
    def targets_coordinator(cls, shape: "EnumExecutionShape") -> bool:
        """
        Check if the execution shape targets a coordination node (orchestrator).

        Coordination nodes (orchestrators) manage workflow execution and
        emit actions to downstream nodes. Both events and commands can
        trigger orchestrators.

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets an orchestrator, False otherwise

        Example:
            >>> EnumExecutionShape.targets_coordinator(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            True
            >>> EnumExecutionShape.targets_coordinator(EnumExecutionShape.COMMAND_TO_ORCHESTRATOR)
            True
            >>> EnumExecutionShape.targets_coordinator(EnumExecutionShape.INTENT_TO_EFFECT)
            False
        """
        return shape in {cls.EVENT_TO_ORCHESTRATOR, cls.COMMAND_TO_ORCHESTRATOR}

    @classmethod
    def targets_effect(cls, shape: "EnumExecutionShape") -> bool:
        """
        Check if the execution shape targets an effect node.

        Effect nodes handle external I/O operations (APIs, databases, files).
        Both intents (from reducers) and commands can target effects.

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets an effect, False otherwise

        Example:
            >>> EnumExecutionShape.targets_effect(EnumExecutionShape.INTENT_TO_EFFECT)
            True
            >>> EnumExecutionShape.targets_effect(EnumExecutionShape.COMMAND_TO_EFFECT)
            True
            >>> EnumExecutionShape.targets_effect(EnumExecutionShape.EVENT_TO_REDUCER)
            False
        """
        return shape in {cls.INTENT_TO_EFFECT, cls.COMMAND_TO_EFFECT}

    @classmethod
    def targets_reducer(cls, shape: "EnumExecutionShape") -> bool:
        """
        Check if the execution shape targets a reducer node.

        Reducer nodes manage FSM state transitions and emit intents. Only
        events can trigger reducers - commands must go through orchestrators.

        Args:
            shape: The execution shape to check

        Returns:
            True if it targets a reducer, False otherwise

        Example:
            >>> EnumExecutionShape.targets_reducer(EnumExecutionShape.EVENT_TO_REDUCER)
            True
            >>> EnumExecutionShape.targets_reducer(EnumExecutionShape.COMMAND_TO_ORCHESTRATOR)
            False
        """
        return shape == cls.EVENT_TO_REDUCER

    @classmethod
    def get_shapes_for_category(
        cls,
        category: EnumMessageCategory,
    ) -> "list[EnumExecutionShape]":
        """
        Get all execution shapes that start with the given message category.

        Useful for discovering what routing options are available for a
        particular message category.

        Args:
            category: The message category to filter by

        Returns:
            List of execution shapes that originate from the given category

        Example:
            >>> shapes = EnumExecutionShape.get_shapes_for_category(EnumMessageCategory.EVENT)
            >>> len(shapes)
            2
            >>> EnumExecutionShape.EVENT_TO_ORCHESTRATOR in shapes
            True
            >>> EnumExecutionShape.EVENT_TO_REDUCER in shapes
            True
        """
        return [shape for shape in cls if cls.get_source_category(shape) == category]

    @classmethod
    def get_shapes_for_target(cls, target_kind: str) -> "list[EnumExecutionShape]":
        """
        Get all execution shapes that target the given node kind.

        Useful for discovering what message flows can reach a particular
        node type.

        Args:
            target_kind: The target node kind as a lowercase string
                (e.g., 'orchestrator', 'effect', 'reducer')

        Returns:
            List of execution shapes targeting that node kind

        Example:
            >>> shapes = EnumExecutionShape.get_shapes_for_target('effect')
            >>> len(shapes)
            2
            >>> EnumExecutionShape.INTENT_TO_EFFECT in shapes
            True
            >>> EnumExecutionShape.COMMAND_TO_EFFECT in shapes
            True
        """
        return [
            shape for shape in cls if cls.get_target_node_kind(shape) == target_kind
        ]

    @classmethod
    def get_description(cls, shape: "EnumExecutionShape") -> str:
        """
        Get a human-readable description of the execution shape.

        Args:
            shape: The execution shape to describe

        Returns:
            A human-readable description explaining the shape's purpose

        Example:
            >>> EnumExecutionShape.get_description(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            'Events routed to orchestrators for workflow coordination'
            >>> EnumExecutionShape.get_description(EnumExecutionShape.INTENT_TO_EFFECT)
            'Intents routed to effects for external actions'
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
