# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""
Dispatch Outputs Model.

Represents a validated list of dispatch output topics with type-safe iteration
and length operations. Provides topic name validation to ensure proper namespace
formatting.

Design Pattern:
    ModelDispatchOutputs is a pure data model that wraps a list of output topic
    names with validation and convenience methods:
    - Topic name validation (must contain namespace separator)
    - Iteration support (__iter__)
    - Length support (__len__)
    - Boolean evaluation (__bool__)

    This model is used by dispatch results and dispatchers to communicate
    which topics received output messages.

Thread Safety:
    ModelDispatchOutputs is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.dispatch import ModelDispatchOutputs
    >>>
    >>> # Create outputs with valid topics
    >>> outputs = ModelDispatchOutputs(topics=[
    ...     "dev.user.events.v1",
    ...     "dev.notification.commands.v1",
    ... ])
    >>>
    >>> # Iteration
    >>> for topic in outputs:
    ...     print(topic)
    dev.user.events.v1
    dev.notification.commands.v1
    >>>
    >>> # Length and boolean evaluation
    >>> len(outputs)
    2
    >>> bool(outputs)
    True
    >>>
    >>> # Empty outputs
    >>> empty = ModelDispatchOutputs()
    >>> len(empty)
    0
    >>> bool(empty)
    False

See Also:
    omnibase_core.models.dispatch.ModelDispatchResult: Uses outputs for dispatch outcomes
"""

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelDispatchOutputs(BaseModel):
    """
    Validated list of dispatch output topics.

    Provides type-safe output topic handling with validation.
    Supports iteration, length, and boolean operations.

    Attributes:
        topics: List of topics where dispatcher outputs were published.
            Each topic must contain at least one dot for namespace separation.

    Example:
        >>> outputs = ModelDispatchOutputs(topics=["dev.user.events.v1"])
        >>> len(outputs)
        1
        >>> list(outputs)
        ['dev.user.events.v1']
        >>> bool(outputs)
        True
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    topics: list[str] = Field(
        default_factory=list,
        description="List of topics where dispatcher outputs were published.",
    )

    @field_validator("topics")
    @classmethod
    def validate_topic_names(cls, v: list[str]) -> list[str]:
        """Validate that each topic name contains proper namespace formatting.

        Topics must contain at least one dot to indicate namespace separation
        (e.g., "dev.user.events.v1", "prod.orders.commands.v2").

        Args:
            v: List of topic names to validate.

        Returns:
            The validated list of topic names.

        Raises:
            ValueError: If any topic is empty or does not contain a dot.

        Example:
            >>> ModelDispatchOutputs(topics=["valid.topic"])  # OK
            >>> ModelDispatchOutputs(topics=["invalid"])  # Raises ValueError

        See Also:
            omnibase_core.models.dispatch.ModelDispatchResult: Dispatch operation result
        """
        for topic in v:
            if not topic:
                msg = "Topic name cannot be empty."
                raise ValueError(msg)
            if "." not in topic:
                msg = (
                    f"Invalid topic format: '{topic}'. "
                    "Topics must contain at least one dot for namespace separation."
                )
                raise ValueError(msg)
        return v

    def __len__(self) -> int:
        """Return the number of output topics.

        Returns:
            Number of topics in this outputs collection.

        Example:
            >>> outputs = ModelDispatchOutputs(topics=["a.b", "c.d"])
            >>> len(outputs)
            2
        """
        return len(self.topics)

    # NOTE: Intentionally overrides BaseModel.__iter__ which iterates over field names.
    # For ModelDispatchOutputs, iteration semantics are over topic strings instead.
    # Why: Runtime protocol compatibility keeps this narrower implementation signature.
    def __iter__(self) -> Iterator[str]:  # type: ignore[override]  # NOTE: intentional semantic override
        """Iterate over output topics.

        This intentionally overrides Pydantic's BaseModel.__iter__ which iterates
        over field names. For ModelDispatchOutputs, iteration semantics are over
        the topic strings, providing natural collection-like behavior.

        Yields:
            Each topic name in the outputs collection.

        Example:
            >>> outputs = ModelDispatchOutputs(topics=["a.b", "c.d"])
            >>> for topic in outputs:
            ...     print(topic)
            a.b
            c.d
        """
        return iter(self.topics)

    def __bool__(self) -> bool:
        """Check if there are any output topics.

        Warning:
            **Non-standard __bool__ behavior**: This model overrides ``__bool__`` to
            return ``True`` only when the topics list is non-empty. This differs from
            typical Pydantic model behavior where ``bool(model)`` always returns ``True``
            for any valid model instance.

        Returns:
            True if there is at least one topic, False otherwise.

        Example:
            >>> bool(ModelDispatchOutputs(topics=["a.b"]))
            True
            >>> bool(ModelDispatchOutputs())
            False
        """
        return bool(self.topics)


__all__ = ["ModelDispatchOutputs"]
