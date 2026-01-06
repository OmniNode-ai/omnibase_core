"""
Subject Type Enum.

Provides type-safe classification of subject types that can own memory snapshots,
enabling filtering and scoping of memory beyond just agents.
"""

from enum import Enum, unique


@unique
class EnumSubjectType(str, Enum):
    """Subject types for memory ownership classification.

    Each memory snapshot can be owned by different types of subjects,
    enabling flexible scoping and filtering of memory data. This enum
    supports the omnimemory system for multi-tenant memory management
    across agents, users, workflows, and organizational contexts.

    Example:
        >>> subject_type = EnumSubjectType.AGENT
        >>> str(subject_type)
        'agent'

        >>> # Use with Pydantic (string coercion works)
        >>> from pydantic import BaseModel
        >>> class MemorySnapshot(BaseModel):
        ...     subject_type: EnumSubjectType
        >>> snapshot = MemorySnapshot(subject_type="workflow")
        >>> snapshot.subject_type == EnumSubjectType.WORKFLOW
        True

        >>> # Filter by subject type
        >>> subject_types = [EnumSubjectType.AGENT, EnumSubjectType.USER]
        >>> agent_types = [s for s in subject_types if s == EnumSubjectType.AGENT]
        >>> len(agent_types)
        1
    """

    AGENT = "agent"
    """Memory owned by an AI agent."""

    USER = "user"
    """Memory owned by a human user."""

    WORKFLOW = "workflow"
    """Memory scoped to a workflow execution."""

    PROJECT = "project"
    """Memory scoped to a project context."""

    SERVICE = "service"
    """Memory owned by a system service."""

    ORG = "org"
    """Memory scoped to an organization."""

    TASK = "task"
    """Memory scoped to a specific task."""

    CORPUS = "corpus"
    """Memory associated with a knowledge corpus."""

    SESSION = "session"
    """Ephemeral session memory (temporary, not persisted long-term)."""

    CUSTOM = "custom"
    """Escape hatch for forward-compatibility with new subject types."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string value is a valid enum member.

        Args:
            value: The string value to check.

        Returns:
            True if the value is a valid enum member, False otherwise.

        Example:
            >>> EnumSubjectType.is_valid("agent")
            True
            >>> EnumSubjectType.is_valid("invalid_type")
            False
        """
        return value in cls._value2member_map_

    def is_entity_type(self) -> bool:
        """Check if this subject type represents an entity (agent, user, or service).

        Returns:
            True if this is an entity-type subject.

        Example:
            >>> EnumSubjectType.AGENT.is_entity_type()
            True
            >>> EnumSubjectType.WORKFLOW.is_entity_type()
            False
        """
        return self in {
            EnumSubjectType.AGENT,
            EnumSubjectType.USER,
            EnumSubjectType.SERVICE,
        }

    def is_scope_type(self) -> bool:
        """Check if this subject type represents a scope (workflow, project, etc.).

        Returns:
            True if this is a scope-type subject.

        Example:
            >>> EnumSubjectType.WORKFLOW.is_scope_type()
            True
            >>> EnumSubjectType.AGENT.is_scope_type()
            False
        """
        return self in {
            EnumSubjectType.WORKFLOW,
            EnumSubjectType.PROJECT,
            EnumSubjectType.ORG,
            EnumSubjectType.TASK,
            EnumSubjectType.SESSION,
            EnumSubjectType.CORPUS,
        }

    def is_persistent(self) -> bool:
        """Check if this subject type typically has persistent (long-term) memory.

        Returns:
            True if memory for this subject type is typically persisted long-term.

        Example:
            >>> EnumSubjectType.AGENT.is_persistent()
            True
            >>> EnumSubjectType.SESSION.is_persistent()
            False
        """
        return self not in {EnumSubjectType.SESSION}


__all__ = ["EnumSubjectType"]
