"""
Subject Type Enum.

Provides type-safe classification of subject types that can own memory snapshots,
enabling filtering and scoping of memory beyond just agents.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSubjectType(StrValueHelper, str, Enum):
    """Memory subject type classification for omnimemory snapshots.

    Classifies the ownership and scope of memory subjects in the omnimemory system,
    enabling flexible multi-tenant memory management across agents, users, workflows,
    and organizational contexts. Each memory snapshot is associated with a subject
    type to support filtering, access control, and lifecycle management.

    See Also:
        - docs/omnimemory/memory_snapshots.md: Memory snapshot architecture
        - EnumDecisionType: Classification of decisions recorded in memory
        - EnumFailureType: Classification of failures recorded in memory

    Values:
        AGENT: Memory owned by an AI agent
        USER: Memory owned by a human user
        WORKFLOW: Memory scoped to a workflow execution
        PROJECT: Memory scoped to a project context
        SERVICE: Memory owned by a system service
        ORG: Memory scoped to an organization
        TASK: Memory scoped to a specific task
        CORPUS: Memory associated with a knowledge corpus
        SESSION: Ephemeral session memory (not persisted long-term)
        CUSTOM: Forward-compatibility escape hatch for new subject types

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
    """Escape hatch for forward-compatibility with new subject types.

    Note: CUSTOM intentionally returns False for both is_entity_type() and
    is_scope_type() as it represents an undefined category. Use application-level
    logic to handle CUSTOM subject types appropriately. However, is_persistent()
    returns True by default (only SESSION is non-persistent).
    """

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

        Note:
            CUSTOM returns False as it represents an undefined category.

        Example:
            >>> EnumSubjectType.AGENT.is_entity_type()
            True
            >>> EnumSubjectType.WORKFLOW.is_entity_type()
            False
            >>> EnumSubjectType.CUSTOM.is_entity_type()
            False
        """
        return self in {
            EnumSubjectType.AGENT,
            EnumSubjectType.SERVICE,
            EnumSubjectType.USER,
        }

    def is_scope_type(self) -> bool:
        """Check if this subject type represents a scope (workflow, project, etc.).

        Returns:
            True if this is a scope-type subject.

        Note:
            CUSTOM returns False as it represents an undefined category.

        Example:
            >>> EnumSubjectType.WORKFLOW.is_scope_type()
            True
            >>> EnumSubjectType.AGENT.is_scope_type()
            False
            >>> EnumSubjectType.CUSTOM.is_scope_type()
            False
        """
        return self in {
            EnumSubjectType.CORPUS,
            EnumSubjectType.ORG,
            EnumSubjectType.PROJECT,
            EnumSubjectType.SESSION,
            EnumSubjectType.TASK,
            EnumSubjectType.WORKFLOW,
        }

    def is_persistent(self) -> bool:
        """Check if this subject type typically has persistent (long-term) memory.

        Returns:
            True if memory for this subject type is typically persisted long-term.

        Note:
            CUSTOM returns True (only SESSION is non-persistent).

        Example:
            >>> EnumSubjectType.AGENT.is_persistent()
            True
            >>> EnumSubjectType.SESSION.is_persistent()
            False
            >>> EnumSubjectType.CUSTOM.is_persistent()
            True
        """
        return self not in {EnumSubjectType.SESSION}


__all__ = ["EnumSubjectType"]
