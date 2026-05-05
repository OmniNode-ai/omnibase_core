# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumUnavailableMode — skill unavailability presentation modes."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumUnavailableMode(StrValueHelper, str, Enum):
    """
    How a skill presents itself when its scope is not satisfied.

    Attributes:
        HIDDEN: Skill not registered; not visible in autocomplete.
        NOOP:   Registered; invocation returns immediately with no output.
        WARN:   Registered; invocation prints a one-line "skill unavailable" notice.
        BLOCK:  Registered; invocation prints a structured error with reasons.

    Example:
        >>> EnumUnavailableMode.HIDDEN.value
        'hidden'
    """

    HIDDEN = "hidden"
    """Skill not registered. Not visible in autocomplete or /help output."""

    NOOP = "noop"
    """Registered but silent. Invocation returns immediately with no output."""

    WARN = "warn"
    """Registered. Invocation prints one-line 'skill unavailable' notice."""

    BLOCK = "block"
    """Registered. Invocation prints structured error explaining unavailability."""


__all__ = ["EnumUnavailableMode"]
