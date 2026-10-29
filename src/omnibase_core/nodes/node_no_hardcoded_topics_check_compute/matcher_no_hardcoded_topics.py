# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure line and path matchers of the no-hardcoded-topics check (OMN-20074, OMN-21518).

Ported from onex_change_control (``check-hardcoded-topics``, pinned fleet rev
8d7e85bc00e7). The decisions are the source's, not those of
``node_hardcoded_topic_check_compute`` or ``validator_hardcoded_topics``: a quoted
topic literal on a line that is not a comment, a docstring line or a block-comment
line, in a file that is neither a test file, an authoritative wire schema nor one
of the approved basenames.

Every pattern, name list, threshold and message is a field of
``ModelNoHardcodedTopicsRules``, loaded from the rule rows of
``validation/contracts/no_hardcoded_topics.validation.yaml``; this module holds none.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_rules import (
    ModelNoHardcodedTopicsRules,
)

__all__ = ["is_exempt_path", "violation_lines"]


@lru_cache(maxsize=32)
def _pattern(source: str) -> re.Pattern[str]:
    return re.compile(source)


def _is_test_file(path: str, rules: ModelNoHardcodedTopicsRules) -> bool:
    """Return True if *path* looks like a test file."""
    if rules.test_dir_marker in path:
        return True
    basename = Path(path).name
    if basename.startswith(rules.test_name_prefix):
        return True
    return basename.endswith(rules.test_name_suffixes)


def _is_wire_schema_contract(path: str, rules: ModelNoHardcodedTopicsRules) -> bool:
    """Return True if *path* is an authoritative wire schema YAML contract."""
    parts = Path(path).as_posix().split("/")
    return (
        len(parts) >= rules.wire_schema_min_parts
        and parts[-2] == rules.wire_schema_dir
        and _pattern(rules.wire_schema_name_pattern).fullmatch(parts[-1]) is not None
    )


def is_exempt_path(path: str, rules: ModelNoHardcodedTopicsRules) -> bool:
    """Return True if no line of the file at *path* is ever flagged."""
    if Path(path).name in rules.approved_basenames:
        return True
    if _is_test_file(path, rules):
        return True
    return _is_wire_schema_contract(path, rules)


def _update_block_comment(
    stripped: str, rules: ModelNoHardcodedTopicsRules, *, in_block: bool
) -> bool:
    """Return updated ``in_block_comment`` state for a single line."""
    opener, closer = rules.block_comment_open, rules.block_comment_close
    if in_block:
        return closer not in stripped
    return opener in stripped and (
        closer not in stripped or stripped.index(opener) > stripped.index(closer)
    )


def _update_docstring(
    stripped: str, rules: ModelNoHardcodedTopicsRules, *, in_docstring: bool
) -> bool:
    """Return updated ``in_docstring`` state for a single line."""
    for delim in rules.docstring_delimiters:
        # One delimiter opens or closes; two on the same line leave the state unchanged.
        if stripped.count(delim) == 1:
            in_docstring = not in_docstring
    return in_docstring


def violation_lines(text: str, rules: ModelNoHardcodedTopicsRules) -> list[int]:
    """Return the 1-based numbers of the lines that hold a flagged literal."""
    literal = _pattern(rules.topic_literal_pattern)
    flagged: list[int] = []
    in_docstring = False
    in_block_comment = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        # JS/TS/CSS block comments: /* ... */
        in_block_comment = _update_block_comment(
            stripped, rules, in_block=in_block_comment
        )
        if in_block_comment or stripped.startswith(rules.block_comment_close):
            continue
        # Triple-quote docstrings (simple heuristic).
        in_docstring = _update_docstring(stripped, rules, in_docstring=in_docstring)
        if in_docstring or stripped.startswith(rules.comment_prefixes):
            continue
        if literal.search(line):
            flagged.append(lineno)
    return flagged
