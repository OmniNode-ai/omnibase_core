# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Function context metadata for the raw environment access validator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class _FunctionContext:
    """The lexical context needed to recognize the sole capture operation."""

    name: str
    is_classmethod: bool
