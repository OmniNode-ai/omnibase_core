"""
Subject type enum for memory ownership.

Provides type-safe classification of subject types that can own memory snapshots,
enabling filtering and scoping of memory beyond just agents.
"""

from enum import Enum


class EnumSubjectType(str, Enum):
    """Subject types for memory ownership.

    Each memory snapshot can be owned by different types of subjects,
    enabling flexible scoping and filtering of memory data.

    Attributes:
        AGENT: Memory owned by an AI agent
        USER: Memory owned by a human user
        WORKFLOW: Memory scoped to a workflow execution
        PROJECT: Memory scoped to a project context
        SERVICE: Memory owned by a system service
        ORG: Memory scoped to an organization
        TASK: Memory scoped to a specific task
        CORPUS: Memory associated with a knowledge corpus
        SESSION: Ephemeral session memory (temporary, not persisted long-term)
        CUSTOM: Escape hatch for forward-compatibility with new subject types
    """

    AGENT = "agent"
    USER = "user"
    WORKFLOW = "workflow"
    PROJECT = "project"
    SERVICE = "service"
    ORG = "org"
    TASK = "task"
    CORPUS = "corpus"
    SESSION = "session"
    CUSTOM = "custom"
