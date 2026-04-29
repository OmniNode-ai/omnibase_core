# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime selection mode enum."""

from enum import Enum, unique


@unique
class EnumRuntimeSelectionMode(str, Enum):
    """Selection strategy for choosing a runtime target."""

    EXPLICIT = "explicit"
    """Target an exact runtime address."""

    CAPABILITY = "capability"
    """Target any runtime matching required capabilities."""

    LOAD_BALANCED = "load_balanced"
    """Target a load-balanced runtime from matching candidates."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = ["EnumRuntimeSelectionMode"]
