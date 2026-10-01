# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared lexical constraints for goal admission models."""

import re

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def is_canonical_git_head_ref(value: str) -> bool:
    """Return whether ``value`` is a safe, fully qualified branch ref."""
    if not value.startswith("refs/heads/"):
        return False
    branch = value.removeprefix("refs/heads/")
    if not branch:
        return False
    if branch.startswith("/"):
        return False
    if branch.endswith(("/", ".")):
        return False
    if any(token in branch for token in ("..", "//", "@{")):
        return False
    return all(
        part not in {"", ".", ".."}
        and not part.startswith(".")
        and not part.endswith(".lock")
        and re.fullmatch(r"[A-Za-z0-9._-]+", part) is not None
        for part in branch.split("/")
    )
