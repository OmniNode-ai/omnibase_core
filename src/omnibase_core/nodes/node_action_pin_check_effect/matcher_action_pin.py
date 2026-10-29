# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure matcher of the action-pin check (OMN-17427, OMN-21518).

``uses:`` extraction, the workflow-file filter and the ref predicates. No
filesystem, no clock; every pattern comes from the typed rule data
(``ModelActionPinRules``) and the organisation, tag pattern and exceptions are
the overlay's, never constants here.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import PurePosixPath

from omnibase_core.models.action_pins.model_action_pin_rules import (
    ModelActionPinRules,
)

__all__ = [
    "extract_uses",
    "is_candidate",
    "is_full_sha",
    "is_local",
    "split_ref",
]


@lru_cache(maxsize=32)
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def is_full_sha(ref: str | None, rules: ModelActionPinRules) -> bool:
    """True when ``ref`` fully matches the rule data's commit sha pattern."""
    return ref is not None and _re(rules.full_sha_pattern).fullmatch(ref) is not None


def is_candidate(path: str, rules: ModelActionPinRules) -> bool:
    """True for a file directly under the workflow directory with a workflow suffix."""
    posix = PurePosixPath(path)
    return posix.parent == PurePosixPath(rules.workflow_dir) and (
        posix.suffix in rules.workflow_suffixes
    )


def extract_uses(
    source: str, rules: ModelActionPinRules
) -> tuple[tuple[int, str], ...]:
    """``(line number, uses value)`` for every ``uses`` key, 1-based.

    Reads block keys (plain or quoted, with or without a list dash) and keys
    inside flow mappings; a whole-line comment is skipped.
    """
    found: list[tuple[int, str]] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        matches: list[re.Match[str]] = []
        block = _re(rules.block_uses_pattern).match(line)
        if block is not None:
            matches.append(block)
        matches.extend(_re(rules.flow_uses_pattern).finditer(line))
        for match in matches:
            value = next(group for group in match.groups() if group is not None)
            found.append((number, value))
    return tuple(found)


def is_local(value: str, rules: ModelActionPinRules) -> bool:
    """A local composite or reusable workflow carries no external ref."""
    return value.startswith(rules.local_prefixes)


def split_ref(value: str) -> tuple[str, str | None]:
    """Split ``owner/repo/path@ref`` into ``(action, ref)``; ref is None when absent."""
    if "@" not in value:
        return value, None
    action, _, ref = value.rpartition("@")
    return action, ref
