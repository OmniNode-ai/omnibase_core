# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic raw-byte secret detection for artifact writes."""

from __future__ import annotations

import re

_DEFAULT_SECRET_PATTERNS: tuple[re.Pattern[bytes], ...] = (
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(rb"ghp_[0-9A-Za-z]{36}"),
    re.compile(rb"xox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(rb"sk-[0-9A-Za-z]{20,}"),
)


class SecretDetector:
    """Pattern-based secret detector for the raw-write gate.

    Stateless and deterministic. Callers may supply their own patterns; the
    default set targets high-signal credential shapes only.
    """

    def __init__(self, patterns: tuple[re.Pattern[bytes], ...] | None = None) -> None:
        self._patterns = patterns if patterns is not None else _DEFAULT_SECRET_PATTERNS

    def contains_secret(self, data: bytes) -> bool:
        """Return whether ``data`` matches any configured secret pattern."""
        return any(pattern.search(data) for pattern in self._patterns)


__all__ = ["SecretDetector"]
