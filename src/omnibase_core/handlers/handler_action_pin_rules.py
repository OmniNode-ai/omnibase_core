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
# ``uses: <action>@<ref>`` as a block key (optionally a list item and a quoted key). An
# unquoted value runs to the first whitespace, so ``#`` inside a ref belongs to the ref
# and only whitespace followed by ``#`` starts a comment.
_BLOCK_USES: Final[re.Pattern[str]] = re.compile(
    r"""^\s*(?:-\s*)?["']?uses["']?\s*:\s*(?:"([^"]*)"|'([^']*)'|(\S+))"""
)
# ``{uses: <action>@<ref>}`` inside a flow mapping.
_FLOW_USES: Final[re.Pattern[str]] = re.compile(
    r"""[{,]\s*["']?uses["']?\s*:\s*(?:"([^"]*)"|'([^']*)'|([^\s,}]+))"""
)


def is_candidate(path: str) -> bool:
    """True for a file directly under ``.github/workflows`` ending in ``.yml``/``.yaml``."""
    posix = PurePosixPath(path)
    return posix.parent == PurePosixPath(".github/workflows") and posix.suffix in (
        ".yml",
        ".yaml",
    )


def extract_uses(source: str) -> tuple[tuple[int, str], ...]:
    """``(line number, uses value)`` for every ``uses`` key, 1-based.

    Reads block keys (plain or quoted, with or without a list dash) and keys
    inside flow mappings; a whole-line comment is skipped.
    """
    found: list[tuple[int, str]] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        matches: list[re.Match[str]] = []
        block = _BLOCK_USES.match(line)
        if block is not None:
            matches.append(block)
        matches.extend(_FLOW_USES.finditer(line))
        for match in matches:
            value = next(group for group in match.groups() if group is not None)
            found.append((number, value))
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
