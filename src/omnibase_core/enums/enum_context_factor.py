# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context factor enum for context pack pipeline."""

from __future__ import annotations

from enum import Enum


class EnumContextFactor(str, Enum):
    """Factor type used to categorize a context chunk in a context pack."""

    GOLDEN_CHAIN = "golden_chain"
    EXEMPLAR = "exemplar"
    LOCAL_FAILURES = "local_failures"
    ARCHITECTURE_PATTERNS = "architecture_patterns"
    CLAUDE_MD = "claude_md"


__all__ = [
    "EnumContextFactor",
]
