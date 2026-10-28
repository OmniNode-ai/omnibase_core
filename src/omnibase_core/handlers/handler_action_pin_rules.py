# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure rules of the action-pin check (OMN-17427).

``uses:`` extraction, the workflow-file filter and the ref predicates. No
filesystem, no clock; the organisation, tag pattern and exceptions are the
overlay's, never constants here.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Final

__all__ = [
    "FULL_SHA",
    "VALIDATOR_ID",
    "extract_uses",
    "is_candidate",
    "is_local",
    "split_ref",
]

VALIDATOR_ID: Final[str] = "action-pins"

# A third-party pin is exactly 40 hex characters.
FULL_SHA: Final[re.Pattern[str]] = re.compile(r"[0-9a-fA-F]{40}")
# ``uses: <action>@<ref>``: tolerate a list dash, quotes and a trailing comment.
_USES: Final[re.Pattern[str]] = re.compile(
    r"""^\s*(?:-\s*)?uses:\s*["']?([^"'#\s]+)["']?"""
)


def is_candidate(path: str) -> bool:
    """True for a file directly under ``.github/workflows`` ending in ``.yml``/``.yaml``."""
    posix = PurePosixPath(path)
    return posix.parent == PurePosixPath(".github/workflows") and posix.suffix in (
        ".yml",
        ".yaml",
    )


def extract_uses(source: str) -> tuple[tuple[int, str], ...]:
    """``(line number, uses value)`` for every ``uses:`` line, 1-based."""
    found: list[tuple[int, str]] = []
    for number, line in enumerate(source.splitlines(), start=1):
        match = _USES.match(line)
        if match:
            found.append((number, match.group(1)))
    return tuple(found)


def is_local(value: str) -> bool:
    """A local ``./`` composite or reusable workflow carries no external ref."""
    return value.startswith(("./", ".\\"))


def split_ref(value: str) -> tuple[str, str | None]:
    """Split ``owner/repo/path@ref`` into ``(action, ref)``; ref is None when absent."""
    if "@" not in value:
        return value, None
    action, _, ref = value.rpartition("@")
    return action, ref
