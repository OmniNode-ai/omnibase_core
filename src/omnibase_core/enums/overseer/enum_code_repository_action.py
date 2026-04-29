# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumCodeRepositoryAction(StrEnum):
    """Actions the overseer can request from a code repository provider.

    Used in protocol dispatch to code repo integrations (e.g. GitHub, GitLab).
    """

    CLONE = "CLONE"
    """Clone a repository to local or remote workspace."""

    FETCH = "FETCH"
    """Fetch latest refs without merging."""

    PULL = "PULL"
    """Pull and fast-forward the working branch."""

    PUSH = "PUSH"
    """Push a branch or tag to origin."""

    CREATE_BRANCH = "CREATE_BRANCH"
    """Create a new branch from a given ref."""

    DELETE_BRANCH = "DELETE_BRANCH"
    """Delete a branch from origin."""

    CREATE_PULL_REQUEST = "CREATE_PULL_REQUEST"
    """Open a pull request for review."""

    MERGE_PULL_REQUEST = "MERGE_PULL_REQUEST"
    """Merge an approved pull request."""

    CREATE_COMMIT = "CREATE_COMMIT"
    """Stage and commit changes."""

    GET_FILE = "GET_FILE"
    """Retrieve file contents at a given ref."""

    LIST_FILES = "LIST_FILES"
    """List files at a given ref and path."""

    GET_DIFF = "GET_DIFF"
    """Retrieve a diff between two refs."""


__all__: list[str] = ["EnumCodeRepositoryAction"]
