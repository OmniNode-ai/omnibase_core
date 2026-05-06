# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumScopeToken — named topology classes for cwd_in predicate resolution.

A scope token is a symbolic label that the scope registry resolves from the
current working directory (and related runtime state) during predicate
evaluation. The registry is the ONLY authoritative source of machine-specific
path knowledge; tokens are stable cross-machine identifiers.

Token resolution order: cwd → git remote → OMNI_HOME env → registry lookup.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumScopeToken(StrValueHelper, str, Enum):
    """
    Named topology classes used in ``cwd_in`` scope predicates.

    These tokens let scope predicates stay machine-independent. The scope
    registry (introduced in OMN-9905) maps runtime cwd to the matching token
    via ``is_omninode_repo`` and its successor matchers.

    ``cwd_in: [omninode_repo]`` matches any clone or worktree of an OmniNode
    repository regardless of its absolute path on disk.

    Attributes:
        OMNINODE_REPO:   Any OmniNode-managed git repository.
        OMNINODE_WORKTREE: A git worktree under $OMNI_HOME/omni_worktrees/.
        OMNINODE_HOME:   The canonical omni_home registry root.
        EXTERNAL_REPO:   Any non-OmniNode repository.
        UNKNOWN:         Could not resolve cwd to a known topology class.

    Example:
        >>> EnumScopeToken.OMNINODE_REPO.value
        'omninode_repo'
    """

    OMNINODE_REPO = "omninode_repo"
    """Any OmniNode-managed git repository (clone or worktree)."""

    OMNINODE_WORKTREE = "omninode_worktree"
    """A git worktree under $OMNI_HOME/omni_worktrees/."""

    OMNINODE_HOME = "omninode_home"
    """The canonical omni_home registry root ($OMNI_HOME)."""

    EXTERNAL_REPO = "external_repo"
    """Any repository not managed by OmniNode tooling."""

    UNKNOWN = "unknown"
    """Could not resolve cwd to a known topology class."""

    def is_omninode_context(self) -> bool:
        """Return True if this token indicates an OmniNode-managed context."""
        return self in (
            EnumScopeToken.OMNINODE_REPO,
            EnumScopeToken.OMNINODE_WORKTREE,
            EnumScopeToken.OMNINODE_HOME,
        )


__all__ = ["EnumScopeToken"]
