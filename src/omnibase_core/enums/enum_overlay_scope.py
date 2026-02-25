# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Overlay Scope Enumeration for Contract Merge Engine.

This module defines EnumOverlayScope, which represents the precedence tiers
at which contract overlays may be applied. The canonical ordering is:

    BASE → ORG → PROJECT → ENV → USER → SESSION

Each level overrides values from all lower levels when overlays are stacked
in a multi-patch pipeline.

See Also:
    - OMN-2757: Overlay stacking — multi-patch pipeline
    - ModelOverlayStackEntry: Uses this enum to declare overlay scope
    - ContractMergeEngine: Applies ordered overlay stacks

.. versionadded:: 0.18.0
    Added as part of overlay stacking pipeline (OMN-2757)
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOverlayScope(StrValueHelper, str, Enum):
    """
    Precedence tiers for contract overlay application.

    Overlays are applied in ascending order of scope level. A higher scope
    overrides values set by lower scopes. The canonical order from lowest
    to highest precedence is:

        BASE → ORG → PROJECT → ENV → USER → SESSION

    Attributes:
        BASE: Lowest precedence. Default platform-wide baseline values.
        ORG: Organisation-level overrides.
        PROJECT: Project-level overrides.
        ENV: Environment-level overrides (staging, production, etc.).
        USER: Per-user customisations.
        SESSION: Highest precedence. Per-session ephemeral overrides.

    Example:
        >>> from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
        >>>
        >>> scope = EnumOverlayScope.PROJECT
        >>> assert scope.value == "project"
        >>> assert str(scope) == "project"
        >>> assert repr(scope) == "EnumOverlayScope.PROJECT"

    Note:
        When validating ordering, compare using SCOPE_ORDER which maps each
        scope to an integer precedence (higher value = higher precedence).

    .. versionadded:: 0.18.0
    """

    BASE = "base"
    """Lowest precedence — platform-wide baseline values."""

    ORG = "org"
    """Organisation-level overrides applied above BASE."""

    PROJECT = "project"
    """Project-level overrides applied above ORG."""

    ENV = "env"
    """Environment-level overrides (e.g. staging, production) applied above PROJECT."""

    USER = "user"
    """Per-user customisations applied above ENV."""

    SESSION = "session"
    """Highest precedence — per-session ephemeral overrides applied above USER."""

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"EnumOverlayScope.{self.name}"


# Canonical ordering map — higher integer = higher precedence.
SCOPE_ORDER: dict[EnumOverlayScope, int] = {
    EnumOverlayScope.BASE: 0,
    EnumOverlayScope.ORG: 1,
    EnumOverlayScope.PROJECT: 2,
    EnumOverlayScope.ENV: 3,
    EnumOverlayScope.USER: 4,
    EnumOverlayScope.SESSION: 5,
}


__all__ = [
    "EnumOverlayScope",
    "SCOPE_ORDER",
]
