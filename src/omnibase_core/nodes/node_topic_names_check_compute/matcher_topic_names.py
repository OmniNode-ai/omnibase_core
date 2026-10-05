# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Core-script regex extraction and first-error topic validation."""

from __future__ import annotations

import re
from pathlib import PurePath
from typing import Final

from omnibase_core.utils.util_topic_suffix import check_topic_suffix

VALIDATOR_ID: Final[str] = "arch-topic-names"
PY_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^[ \t]*(?:TOPIC_|SUFFIX_)\w+\s*[:=]\s*["\']([^"\']+)["\']""",
    re.MULTILINE,
)
TS_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^[ \t]*export\s+const\s+(?:TOPIC_|SUFFIX_)\w+\s*=\s*["\']([^"\']+)["\']""",
    re.MULTILINE,
)
FLAT_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9-]*$")
ENV_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\{env\}\.")


def extract_topics(path: str, source: str) -> list[tuple[int, str]]:
    """Reproduce the oracle's extension selection, values and match-start lines."""
    suffix = PurePath(path).suffix.lower()
    if suffix == ".py":
        pattern = PY_TOPIC_PATTERN
    elif suffix == ".ts":
        pattern = TS_TOPIC_PATTERN
    else:
        return []
    return [
        (source[: match.start()].count("\n") + 1, match.group(1))
        for match in pattern.finditer(source)
    ]


def topic_error(value: str) -> tuple[str, str] | None:
    """Return a rule and byte-identical message, preserving validation order."""
    if ENV_PREFIX_PATTERN.match(value):
        return "env-prefix", f"topic uses {{env}}. prefix (legacy pattern): {value}"
    if FLAT_TOPIC_PATTERN.match(value):
        return (
            "flat-topic",
            f"flat legacy topic name (must use onex.<kind>.<producer>.<event>.v<n>): {value}",
        )
    result = check_topic_suffix(value)
    if not result.is_valid:
        return "canonical-suffix", f"{result.error}: {value}"
    return None
